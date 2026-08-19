from pathlib import Path

from hpc_campaign.info import format_info
from hpc_campaign.ls import ls
from hpc_campaign.manager import Manager
from hpc_campaign.rm import rm

repo_root = Path(__file__).resolve().parents[1]
campaign_store = repo_root
print(f"campaign_store = {repo_root}")
api_archive = "test_tar.aca"  #  will find it in repo_root
heat_tar = "data/tar/heat.tar"
heat_idx = "data/tar/heat.taridx"

expected_datasets = {
    "heat": "ADIOS",
    "onearray": "HDF5",
    "doc/Read.me": "TEXT",
    "img/T0.png": "IMAGE",
    "img/T1.png": "IMAGE",
    "img/T2.png": "IMAGE",
    "img/T3.png": "IMAGE",
    "img/T4.png": "IMAGE",
    "img/T5.png": "IMAGE",
    "img/T6.png": "IMAGE",
    "img/T7.png": "IMAGE",
    "img/T9.png": "DIFFERENT",
    "not_in_result": "WHOKNOWS",
}
info_outputs: dict[str, str] = {}


def print_dict_diff(a: dict[str, str], b: dict[str, str]) -> None:
    for key in sorted(a.keys() | b.keys()):
        if key not in a:
            print(f"  extra  : {key}: {b[key]!r}")
        elif key not in b:
            print(f"  missing: {key}: {a[key]!r}")
        elif a[key] != b[key]:
            print(f"  differ : {key}: {a[key]!r} -> {b[key]!r}")


def main():
    manager = Manager(archive=str(api_archive), campaign_store=str(campaign_store), verbose=5)
    manager.open(create=True, truncate=True)
    assert repo_root.joinpath(api_archive).exists()
    host_id, dir_id, archive_id = manager.add_archival_storage(
        system="fs",
        host="",
        directory=str(repo_root),
        tarfilename=str(heat_tar),
        tarfileidx=str(heat_idx),
    )
    print(f"Archive storage added: host id = {host_id}, directory id = {dir_id} archive id = {archive_id}")

    info_data = manager.info(True, False, False, False)
    output = format_info(info_data)
    print(output)
    manager.close()

    # ls this aca
    result = ls(str(api_archive), campaign_store=str(campaign_store))
    print(f"ls result: {result}")
    assert len(result) == 1
    assert result[0] == str(api_archive)

    result_datasets = {}
    for _, ds in info_data.datasets.items():
        result_datasets[ds.name] = ds.file_format

    print("Expected vs result datasets in campaign file")
    print_dict_diff(expected_datasets, result_datasets)

    # rm this aca


#    result = rm(str(api_archive), campaign_store=str(campaign_store), interactive=True)
#    print(f"rm result: {result}")
#    assert result == [] or result == [str(api_archive)]


if __name__ == "__main__":
    main()
