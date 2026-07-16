"""
Test adding a tar file to a campaign.
Depends on data/ having heat.tar and associated heat.taridx
"""

import argparse
import logging
import subprocess
import sys
from pathlib import Path

from hpc_campaign.info import format_info
from hpc_campaign.ls import ls
from hpc_campaign.manager import Manager
from hpc_campaign.rm import rm

LOGGER = logging.getLogger(__name__)

repo_root = Path(__file__).resolve().parents[1]
campaign_store = repo_root

data_dir = Path("tests/tar")
cmdline_archive = data_dir / "test_cmdline_tar.aca"
api_archive = data_dir / "test_api_tar.aca"
heat_tar = data_dir / "heat.tar"
heat_idx = data_dir / "heat.taridx"

""" expected_datasets = {
    "data/heat.bp": "ADIOS",
    "data/readme": "TEXT",
    "data/T00000.png": "IMAGE",
    "data/T00001.png": "IMAGE",
    "data/T00002.png": "IMAGE",
    "data/T00003.png": "IMAGE",
    "data/T00004.png": "IMAGE",
    "data/T00005.png": "IMAGE",
    "data/T00006.png": "IMAGE",
    "data/T00007.png": "IMAGE",
    "data/T00008.png": "IMAGE",
    "data/T00009.png": "IMAGE",
} """

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
    "img/T8.png": "IMAGE",
    "img/T9.png": "IMAGE",
}

info_outputs: dict[str, str] = {}


def run_manager_command(args: list[str]) -> subprocess.CompletedProcess:
    command = [
        sys.executable,
        "-m",
        "hpc_campaign",
        "manager",
        "--campaign_store",
        str(campaign_store),
    ]
    command.extend([str(entry) for entry in args])
    return subprocess.run(command, check=True, capture_output=True, text=True)


def run_command(cmd: str, args: list[str]) -> subprocess.CompletedProcess:
    command = [
        sys.executable,
        "-m",
        "hpc_campaign",
        cmd,
        "--campaign_store",
        str(campaign_store),
    ]
    command.extend([str(entry) for entry in args])
    return subprocess.run(command, check=True, capture_output=True, text=True)


def normalize_info_output(output_text: str) -> str:
    # remove the first line from CLI output that is like ======..
    lines = output_text.splitlines()
    if lines and lines[0].startswith("=========="):
        lines = lines[1:]
    return "\n".join(lines).strip()


def build_info_args() -> argparse.Namespace:
    return argparse.Namespace(
        list_replicas=True,
        list_files=True,
        show_deleted=True,
        show_checksum=True,
    )


def dict_diff(a: dict[str, str], b: dict[str, str]) -> bool:
    differ = False
    for key in sorted(a.keys() | b.keys()):
        if key not in a:
            LOGGER.debug(f"  extra  : {key}: {b[key]!r}")
            differ = True
        elif key not in b:
            LOGGER.debug(f"  missing: {key}: {a[key]!r}")
            differ = True
        elif a[key] != b[key]:
            LOGGER.debug(f"  differ : {key}: {a[key]!r} -> {b[key]!r}")
            differ = True
    return differ


def test_01_tar_api():
    manager = Manager(archive=str(api_archive), campaign_store=str(campaign_store))
    manager.open(create=True, truncate=True)
    host_id, dir_id, archive_id = manager.add_archival_storage(
        system="fs",
        host="",
        directory=str(data_dir.resolve().parents[0]),
        tarfilename=str(heat_tar),
        tarfileidx=str(heat_idx),
    )
    # manager.add_archival_storage("fs", "", str(heat_tar), str(heat_idx))

    LOGGER.debug(f"Archive storage added: host id = {host_id}, directory id = {dir_id} archive id = {archive_id}")
    # ls this aca
    result = ls(str(api_archive), campaign_store=str(campaign_store))
    print(f"ls result: {result}")
    print(Path.cwd())
    assert api_archive.exists()

    info_data = manager.info(True, False, False, False)
    output = format_info(info_data)
    LOGGER.debug(output)
    manager.close()

    result_datasets = {}
    for _, ds in info_data.datasets.items():
        result_datasets[ds.name] = ds.file_format
    assert not dict_diff(expected_datasets, result_datasets)

    # rm this aca
    result = rm(str(api_archive), campaign_store=str(campaign_store), interactive=False, force=True)
    print(f"rm result: {result}")
    assert result == [] or result == [str(api_archive)]
