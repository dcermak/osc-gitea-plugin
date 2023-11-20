from urllib.parse import urlparse
import xml.etree.ElementTree as ET
import osc.commandline
from osc.conf import get_config
from osc.core import (
    branch_pkg,
    makeurl,
    metafile,
    show_devel_project,
    show_package_meta,
    show_scmsync,
)
from py_gitea_opensuse_org.api.repository_api import RepositoryApi
from py_gitea_opensuse_org.api_client import ApiClient
from py_gitea_opensuse_org.exceptions import ApiException
from py_gitea_opensuse_org.models.create_hook_option import CreateHookOption
from py_gitea_opensuse_org.models.repository import Repository

from osc_gitea_plugin.tea_config import Login, api_client_from_login, load_logins


_API_URL = "https://api.opensuse.org/"

# need to call this for osc's internal state being initialized
get_config()


async def fork_devel_package(
    api_client: ApiClient,
    login: Login,
    pkg_name: str,
    project_name: str = "openSUSE:Factory",
    create_scmsync: bool = True,
) -> None:
    devel_prj, devel_pkg = show_devel_project(_API_URL, pac=pkg_name, prj=project_name)

    if not devel_prj or not devel_pkg:
        raise RuntimeError(f"The package {pkg_name} has no devel project")

    err_begin = f"The package {devel_prj}/{devel_pkg}"
    scmsync = show_scmsync(_API_URL, pac=devel_pkg, prj=devel_prj)
    if not scmsync:
        raise RuntimeError(f"{err_begin} has no scmsync config")

    url = urlparse(scmsync)
    if url.fragment != "factory":
        raise ValueError(f"{err_begin} uses the wrong branch: {url.fragment}")

    if url.netloc not in api_client.configuration.host:
        raise ValueError(f"{err_begin} is synced from the wrong host: {url.netloc}")

    org: str
    gitea_pkg_name: str
    org, gitea_pkg_name = filter(None, url.path.split("/"))
    if org != "pool":
        raise ValueError(
            f"{err_begin} is not synced from the pool organization, got: {org}"
        )

    repo_api = RepositoryApi(api_client)
    try:
        fork = await repo_api.create_fork(org, gitea_pkg_name)
    except ApiException as exc:
        # status 409 means that the fork exists
        if exc.status != 409:
            raise

        def find_matching_repo(forks: list[Repository]) -> Repository | None:
            for fork in forks:
                if fork.owner.login == login.user:
                    return fork
            return None

        forks = await repo_api.list_forks(org, gitea_pkg_name)

        page = 0
        while not (fork := find_matching_repo(forks)) and (
            forks := await repo_api.list_forks(org, gitea_pkg_name, page=page)
        ):
            page += 1

        if not fork:
            raise RuntimeError(
                f"Could not find the user's ({login.user}) fork of {gitea_pkg_name}"
            )

    if not create_scmsync:
        return

    _, targetprj, targetpkg, _, _ = branch_pkg(
        _API_URL, src_project=devel_prj, src_package=devel_pkg, return_existing=True
    )

    assert targetpkg and targetprj

    meta = ET.fromstring(
        b"".join(show_package_meta(_API_URL, prj=targetprj, pac=targetpkg))
    )

    new_url = f"{fork.clone_url}#factory"
    if (scmsync_elem := meta.find("scmsync")) is not None:
        scmsync_elem.text = new_url
    else:
        (scm := ET.Element("scmsync")).text = new_url
        meta.append(scm)

    url = makeurl(_API_URL, ["source", targetprj, targetpkg, "_meta"])
    mf = metafile(url, ET.tostring(meta))
    mf.sync()


class GiteaForkCommand(osc.commandline.OscCommand):
    name = "fork"

    def init_arguments(self) -> None:
        self.add_argument()


def main() -> None:
    import asyncio

    client, login = api_client_from_login(load_logins())
    if not client:
        raise RuntimeError("Could not get a API token from ~/.config/tea/config.yml")

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(fork_devel_package(client, login, "vagrant-libvirt"))
    finally:
        loop.run_until_complete(client.close())
