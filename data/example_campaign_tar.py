from pathlib import Path

from hpc_campaign.info import format_info
from hpc_campaign.ls import ls
from hpc_campaign.manager import Manager
from hpc_campaign.rm import rm

repo_root = Path(__file__).resolve().parents[1]
campaign_store = repo_root
data_dir = Path("data")

print(f"campaign_store = {repo_root}")
print(f"data_dir = {data_dir}")

api_archive = data_dir / "test_tar.aca"
heat_tar = data_dir / "heat.tar"
heat_idx = data_dir / "heat.taridx"

expected_datasets = {
    "data/heat.bp" : "ADIOS",
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
    "data/T00009.png": "IMAGE"
}
info_outputs: dict[str, str] = {}


def main():
    manager = Manager(archive=str(api_archive), campaign_store=str(campaign_store), verbose=5)
    manager.open(create=True, truncate=True)
    assert repo_root.joinpath(api_archive).exists()
    host_id, dir_id, archive_id = manager.add_archival_storage(
       system="fs", host="", directory=str(data_dir.resolve().parents[0]),
       tarfilename=str(heat_tar), tarfileidx=str(heat_idx)
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

    # rm this aca
#    result = rm(str(api_archive), campaign_store=str(campaign_store), interactive=True)
#    print(f"rm result: {result}")
#    assert result == [] or result == [str(api_archive)]


if __name__ == "__main__":
    main()
