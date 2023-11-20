import os
from yaml import safe_load
from pydantic import BaseModel
from py_gitea_opensuse_org.api_client import ApiClient
from py_gitea_opensuse_org.configuration import Configuration


class Login(BaseModel):
    """Single login entry in :file:``tea/config.yml``."""

    name: str
    url: str
    token: str
    user: str


def load_logins() -> list[Login]:
    conf_file = os.path.join(
        os.getenv("XDG_CONFIG_HOME", os.path.expanduser("~/.config")),
        "tea",
        "config.yml",
    )
    conf = safe_load(open(conf_file, "r", encoding="utf-8"))
    res = []

    if "logins" not in conf:
        return []

    for login in conf["logins"]:
        res.append(Login(**login))

    return res


_SRC_O_O = "https://src.opensuse.org"


def api_client_from_login(
    logins: list[Login],
) -> tuple[ApiClient, Login] | tuple[None, None]:
    for login in logins:
        if _SRC_O_O not in login.url:
            continue

        conf = Configuration(
            api_key={(hdr := "AuthorizationHeaderToken"): login.token},
            api_key_prefix={hdr: "token"},
            host=f"{_SRC_O_O}/api/v1",
        )
        return ApiClient(configuration=conf), login

    return None, None
