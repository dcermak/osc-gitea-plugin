import asyncio
from tempfile import TemporaryDirectory, NamedTemporaryFile
import os

from py_gitea_opensuse_org.api.repository_api import RepositoryApi
from py_gitea_opensuse_org.exceptions import NotFoundException

from osc_gitea_plugin.tea_config import api_client_from_login, load_logins

OSC_PASSWORD_ENVVAR_NAME = "OSC_PASSWORD"
OSC_USERNAME_ENVVAR_NAME = "OSC_USER"

GITEA_USER_ENVVAR_NAME = "GITEA_SERVER_USER"
GITEA_TOKEN_ENVVAR_NAME = "GITEA_SERVER_TOKEN"


def before_scenario(context, scenario) -> None:
    tmpdir = TemporaryDirectory()
    context.tmpdir = tmpdir.name
    context.tmpdir_obj = tmpdir


def after_scenario(context, scenario) -> None:
    if tmpdir := getattr(context, "tmpdir_obj", None):
        assert isinstance(tmpdir, TemporaryDirectory)
        tmpdir.cleanup()


def after_feature(context, feature) -> None:
    if not (forks := set(getattr(context, "forks", []))):
        return

    api_client, _ = api_client_from_login(load_logins(context.xdg_config_home_dir.name))
    assert api_client
    repo_api = RepositoryApi(api_client)

    loop = asyncio.get_event_loop()
    for fork in forks:
        try:
            loop.run_until_complete(
                repo_api.repo_delete(owner=context.gitea_user, repo=fork)
            )
        except NotFoundException:
            pass

    context.forks = []


def before_all(context) -> None:
    pw, user, context.gitea_user, context.gitea_token = [
        os.getenv(envvar)
        for envvar in (
            OSC_PASSWORD_ENVVAR_NAME,
            OSC_USERNAME_ENVVAR_NAME,
            GITEA_USER_ENVVAR_NAME,
            GITEA_TOKEN_ENVVAR_NAME,
        )
    ]

    if not context.gitea_user or not context.gitea_token:
        raise RuntimeError(
            f"Environment variables '{GITEA_USER_ENVVAR_NAME}' and '{GITEA_TOKEN_ENVVAR_NAME}'"
        )

    if not pw or not user:
        raise RuntimeError(
            f"Environment variables {OSC_PASSWORD_ENVVAR_NAME} and {OSC_USERNAME_ENVVAR_NAME} have to be set"
        )

    osc_conf = NamedTemporaryFile("w", delete=False)
    osc_conf.write(
        f"""[general]
apiurl = https://api.opensuse.org
[https://api.opensuse.org]
user = {user}
pass = {pw}
aliases = obs
"""
    )
    osc_conf.flush()
    context.osc_conf = osc_conf

    context.osc_user = user
    context.xdg_state_home_dir = TemporaryDirectory()
    context.xdg_config_home_dir = TemporaryDirectory()
    context.env = {
        "XDG_STATE_HOME": context.xdg_state_home_dir.name,
        "XDG_CONFIG_HOME": context.xdg_config_home_dir.name,
    }
    context.osc = f"osc --config={osc_conf.name}"

    context.forks = []


def after_all(context) -> None:
    for temp_dir_attr_name in (
        "xdg_config_home_dir",
        "xdg_state_home_dir",
    ):
        if tmpdir := getattr(context, temp_dir_attr_name, None):
            assert isinstance(tmpdir, TemporaryDirectory)
            tmpdir.cleanup()

    if osc_conf := getattr(context, "osc_conf", None):
        osc_conf.close()
