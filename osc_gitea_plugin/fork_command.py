import typing
import osc.commandline


if typing.TYPE_CHECKING:
    from py_gitea_opensuse_org.api_client import ApiClient
    from osc_gitea_plugin.tea_config import Login
    from py_gitea_opensuse_org.models.repository import Repository


async def fork_devel_package(
    api_client: "ApiClient",
    login: "Login",
    pkg_name: str,
    project_name: str = "openSUSE:Factory",
    create_scmsync: bool = True,
) -> tuple[bool, str]:
    """This function searches for the devel package of ``pkg_name`` in the
    supplied ``project_name``. If the package has a develpackage that is using
    ``<scmsync>`` to ``src.opensuse.org/pool``, then the repository on gitea is
    forked. If a fork already exists then no action is taken.

    Returns
    -------
    - bool: flag indicating whether a fork has been created
    - str: the clone url of the forked repository

    """
    import xml.etree.ElementTree as ET

    from osc_gitea_plugin.common import API_URL, fetch_devel_pkg
    from osc.core import (
        branch_pkg,
        makeurl,
        metafile,
        show_package_meta,
    )

    from py_gitea_opensuse_org.api.repository_api import RepositoryApi
    from py_gitea_opensuse_org.exceptions import ApiException

    devel = fetch_devel_pkg(pkg_name, project_name)

    devel_pkg, devel_prj, org, gitea_pkg_name = (
        devel.devel_pkg,
        devel.devel_prj,
        devel.gitea_org,
        devel.gitea_pkg,
    )

    repo_api = RepositoryApi(api_client)
    created_fork = False
    try:
        fork = await repo_api.create_fork(org, gitea_pkg_name)
        created_fork = True
    except ApiException as exc:
        # status 409 means that the fork exists
        if exc.status != 409:
            raise

        def find_matching_repo(forks: list["Repository"]) -> "Repository | None":
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
            ) from exc

    if create_scmsync:
        _, targetprj, targetpkg, _, _ = branch_pkg(
            API_URL, src_project=devel_prj, src_package=devel_pkg, return_existing=True
        )

        assert targetpkg and targetprj

        meta = ET.fromstring(
            b"".join(show_package_meta(API_URL, prj=targetprj, pac=targetpkg))
        )

        new_url = f"{fork.clone_url}#factory"
        if (scmsync_elem := meta.find("scmsync")) is not None:
            scmsync_elem.text = new_url
        else:
            (scm := ET.Element("scmsync")).text = new_url
            meta.append(scm)

        url = makeurl(API_URL, ["source", targetprj, targetpkg, "_meta"])
        mf = metafile(url, ET.tostring(meta))
        mf.sync()

    return (
        created_fork,
        # ideally gitea should give us a ssh_url, but if that fails, fallback to
        # clone_url and if that is missing too, construct a fallback
        fork.ssh_url
        or fork.clone_url
        or f"https://src.opensuse.org/{login.user}/{gitea_pkg_name}",
    )


class GiteaForkCommand(osc.commandline.OscCommand):
    name = "fork"

    def init_arguments(self) -> None:
        subparsers = self.parser.add_subparsers(dest="action")
        delete_cmd = subparsers.add_parser(
            "delete", help="Delete the fork of the checked out repository"
        )
        # delete_cmd.add_argument("repository", required=False, nargs=1, type=str, help="Repository fork to delete")
        delete_cmd.add_argument(
            "--yes",
            action="store_true",
            help="Don't ask for confirmation and delete immediately",
        )

        self.add_argument(
            "--create-scmsync",
            action="store_true",
            help="Create a package on OBS that is scmsynced from the fork",
        )

    async def create_fork(
        self,
        api_client: "ApiClient",
        login: "Login",
        pkg: str,
        create_scmsync: bool,
        cwd: str,
    ) -> None:
        import subprocess

        try:
            created_fork, clone_url = await fork_devel_package(
                api_client, login, pkg, create_scmsync=create_scmsync
            )

        finally:
            await api_client.close()

        if created_fork:
            print(f"Created fork {clone_url}")
        else:
            print(f"Reusing existing fork {clone_url}")
            subprocess.run(["git", "remote", "remove", login.user], cwd=cwd)

        subprocess.check_output(
            ["git", "remote", "add", login.user, clone_url], cwd=cwd
        )

    async def delete_fork(
        self, api_client: "ApiClient", login: "Login", pkg: str, no_confirm: bool
    ) -> None:
        from py_gitea_opensuse_org.api.repository_api import RepositoryApi

        repo_slug = f"{login.user}/{pkg}"
        if not no_confirm:
            print(
                f"Confirm the deletion of {login.user}/{pkg} by typing its full name:",
                end="",
            )
            if (inp := input()) != repo_slug:
                raise ValueError(f"Invalid repo name {inp}")

        try:
            await RepositoryApi(api_client).repo_delete(login.user, pkg)
            print(f"Removed {repo_slug}")
        finally:
            await api_client.close()

    def run(self, args) -> None:
        import asyncio
        import os
        from osc.store import get_store
        from osc_gitea_plugin.tea_config import api_client_from_login, load_logins

        store = get_store(cwd := os.getcwd(), check=False)
        if store.is_package:
            pkg = store.package
            # if this is a git package, we should add the remote here
        else:
            raise RuntimeError(f"{cwd} is not an osc package")

        client, login = api_client_from_login(load_logins())
        if not client:
            raise RuntimeError(
                "Could not get a API token from ~/.config/tea/config.yml"
            )
        assert login, "login must not be None as client is not None"

        loop = asyncio.get_event_loop()

        try:
            if args.action is None:
                loop.run_until_complete(
                    self.create_fork(client, login, pkg, args.create_scmsync, cwd)
                )
            elif args.action == "delete":
                loop.run_until_complete(self.delete_fork(client, login, pkg, args.yes))
            else:
                assert False, f"got an invalid action {args.action}"
        finally:
            loop.run_until_complete(client.close())
