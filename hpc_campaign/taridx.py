import argparse
import io
import tarfile

from PIL import Image, UnidentifiedImageError

from .types import DatasetType

TARIDX_VERSION = 2
HDF5_HEADER = b"\x89HDF\r\n\x1a\n"

# TARTYPES = {
#     "reg": 0,
#     "lnk": 1,
#     "sym": 2,
#     "chr": 3,
#     "blk": 4,
#     "dir": 5,
#     "fifo": 6,
#     "cont": 7,
#     "longname": 8,
#     "longlink": 9,
#     "sparse": 10,
# }


def create_tar_index_simple(tarfilename: str, indexfile: str | None):
    with tarfile.open(tarfilename) as tf:
        if indexfile is None:
            indexfile = tarfilename + ".idx"
        with open(indexfile, "w", encoding="utf-8") as idxf:
            for ti in tf:
                idxf.write(f'{int(ti.type)},{ti.offset},{ti.offset_data},{ti.size},"{ti.name}"\n')


class TarMemberFile(io.RawIOBase):
    def __init__(self, f, offset_data, size):
        self._f = f
        self._base = offset_data
        self._size = size
        self._pos = 0

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self._pos

    def seek(self, offset, whence=io.SEEK_SET):
        if whence == io.SEEK_SET:
            self._pos = offset
        elif whence == io.SEEK_CUR:
            self._pos += offset
        elif whence == io.SEEK_END:
            self._pos = self._size + offset

        self._pos = max(0, min(self._pos, self._size))
        return self._pos

    def read(self, n=-1):
        if n < 0:
            n = self._size - self._pos

        n = min(n, self._size - self._pos)

        self._f.seek(self._base + self._pos)
        data = self._f.read(n)
        self._pos += len(data)
        return data

    def readinto(self, b):
        data = self.read(len(b))
        n = len(data)
        b[:n] = data
        return n

    def close(self):
        # self._f.close()
        # super().close()
        pass

def is_image_tar_member(tarfile:io.BufferedReader, offset_data: int, size:int ):
    raw = TarMemberFile(tarfile, offset_data, size)
    fobj = io.BufferedReader(raw)

    try:
        with Image.open(fobj) as img:
            img.verify()   # validates image structure
            return True, img.format
    except UnidentifiedImageError:
        return False, None
    except OSError:
        return False, None
    finally:
        fobj.close()

def create_tar_index(tarfilename: str, indexfile: str | None, verbose: int = 0):
    if indexfile is None:
        indexfile = tarfilename + ".idx"

    with (
        tarfile.open(tarfilename) as tf,
        open(indexfile, "w", encoding="utf-8") as idxf,
        open(tarfilename, "rb") as tfbin
    ):
        idxf.write(f"TARIDX_VERSION,{TARIDX_VERSION}\n")
        idxf.write("filetype, offset, offset_data, size, mtime, name\n")
        it = iter(tf)
        readnext = True
        filetype = DatasetType.Unknown
        while True:
            if readnext:
                ti = next(it, None)
            else:
                readnext = True
            if ti is None:
                break

            entrytype = int(ti.type)
            if entrytype not in (0, 5):  # process only Regular and Directory entries
                verbose >= 2 and print(f'Skip: {entrytype},{ti.offset},{ti.offset_data},{ti.size},{ti.mtime}"{ti.name}"\n')
                continue

            # What file is is? HDF5, image, ADIOS-BP or something else?
            verbose >= 3 and print(f'{entrytype},{ti.offset},{ti.offset_data},{ti.size},{ti.mtime},"{ti.name}"')
            if entrytype == 0:
                tfbin.seek(ti.offset_data)
                header = tfbin.read(len(HDF5_HEADER))
                if header == HDF5_HEADER:
                    # This is an HDF5 file
                    filetype = DatasetType.HDF5
                else:
                    is_image, fmt = is_image_tar_member(tfbin, ti.offset_data, ti.size)
                    if is_image:
                        # This is an IMAGE file
                        filetype = DatasetType.IMAGE
                    else:
                        # This is handled as a blob (TEXT)
                        filetype = DatasetType.TEXT

                verbose >= 1 and print(f'{filetype.name}: {ti.offset},{ti.offset_data},{ti.size},{ti.mtime},"{ti.name}"')
                idxf.write(f'{filetype},{ti.offset},{ti.offset_data},{ti.size},{ti.mtime},"{ti.name}"\n')
            else:
                # hunting for ADIOS BP directories
                dirname = ti.name
                foundADIOS = False
                components = [f'{DatasetType.ADIOS},{ti.offset},{ti.offset_data},{ti.size},{ti.mtime},"{ti.name}"\n']
                score = 0
                verbose >= 3 and print(f"Process dir: {ti.name}")
                while True:
                    ti = next(it, None)
                    if ti is None:
                        # No more entries
                        verbose >=3 and print("  no more entries")
                        break
                    if not ti.name.startswith(dirname):
                        # This is something next, need to remember
                        verbose >= 3 and print("  ended directory")
                        break
                    if ti.type != b'0':
                        if foundADIOS:
                            # Something not compatible with ADIOS is in this directory
                            print(f"Unexpected element: believed that {dirname} was an ADIOS dataset"
                                  f" but found a non-file element in it: {ti.name}. Skip this.")
                            continue
                        else:
                            print(f"  incompatible element {ti.type} {ti.name}")
                            break
                    if (ti.name.endswith("md.idx") or
                        ti.name.endswith("md.0") or
                        ti.name.endswith("mmd.0") or
                        ti.name.endswith("data.0")
                        ):
                        score += 1
                        verbose >=3 and print(f"score = {score}")

                    if score >= 2:
                        foundADIOS = True

                    components.append(f'{DatasetType.ADIOS_Subfile},{ti.offset},{ti.offset_data},{ti.size},{ti.mtime},"{ti.name}"\n')

                # we have an item unprocessed or None, skip reading at the beginning of the loop
                readnext = False
                if foundADIOS:
                    verbose >= 1 and print(f"ADIOS: {dirname}")
                    for c in components:
                        verbose >= 2 and print(" ", c[:-1])
                        idxf.write(c)


def _setup_args(args=None, prog=None):
    parser = argparse.ArgumentParser(
        prog=prog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""
Create an index file from a TAR file. It can be used in the
'manager <archive> add-archival-storage' command to make automatic
replicas of all datasets in the archive and register their offsets
and sizes in the TAR file.
""",
    )
    parser.add_argument("tarfile", help="Name of the TAR file", type=str)
    parser.add_argument("idxfile", nargs="?", help="Optional name of the index file", type=str)
    parser.add_argument("--verbose", "-v", help="More verbosity", action="count", default=0)
    args = parser.parse_args(args=args)
    #    if args.idxfile is None:
    #        args.idxfile = args.tarfile + ".idx"
    return args


def main(args=None, prog=None):
    args = _setup_args(args=args, prog=prog)
    create_tar_index(args.tarfile, args.idxfile, args.verbose)
