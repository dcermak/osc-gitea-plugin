from urllib.parse import urlparse
from osc.core import show_devel_project, show_scmsync

from dataclasses import dataclass


@dataclass(frozen=True)
class DevelPackage:
    devel_prj: str
    devel_pkg: str
    gitea_pkg: str
    gitea_org: str


API_URL = "https://api.opensuse.org/"

GITEA_HOSTNAME = "src.opensuse.org"


def fetch_devel_pkg(
    pkg_name: str, project_name: str = "openSUSE:Factory"
) -> DevelPackage:
    devel_prj, devel_pkg = show_devel_project(API_URL, pac=pkg_name, prj=project_name)

    if not devel_prj or not devel_pkg:
        raise RuntimeError(f"The package {pkg_name} has no devel project")

    err_begin = f"The package {devel_prj}/{devel_pkg}"
    scmsync = show_scmsync(API_URL, pac=devel_pkg, prj=devel_prj)
    if not scmsync:
        raise RuntimeError(f"{err_begin} has no scmsync config")

    url = urlparse(scmsync)
    if url.fragment != "factory":
        raise ValueError(f"{err_begin} uses the wrong branch: {url.fragment}")

    if url.netloc not in GITEA_HOSTNAME:
        raise ValueError(f"{err_begin} is synced from the wrong host: {url.netloc}")

    org: str
    gitea_pkg_name: str
    org, gitea_pkg_name = filter(None, url.path.split("/"))
    if org != "pool":
        raise ValueError(
            f"{err_begin} is not synced from the pool organization, got: {org}"
        )
    if gitea_pkg_name.endswith(".git"):
        gitea_pkg_name = gitea_pkg_name[:-4]

    return DevelPackage(
        devel_pkg=devel_pkg,
        devel_prj=devel_prj,
        gitea_pkg=gitea_pkg_name,
        gitea_org=org,
    )
