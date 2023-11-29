import re
import time
from pathlib import Path
import subprocess
import shlex
import os
import os.path

import behave


def run(
    cmd: list[str], cwd: str | None = None, env: dict[str, str] | None = None
) -> tuple[int, str, str]:
    """
    Run a command.
    Return exitcode, stdout, stderr
    """

    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        universal_newlines=True,
        errors="surrogateescape",
    )

    stdout, stderr = proc.communicate()
    return proc.returncode, stdout, stderr


def check_context_exit_code(context) -> None:
    ret, stdout, stderr = [
        getattr(context, attr, None) for attr in ("ret", "stdout", "stderr")
    ]
    if ret is not None and ret != 0:
        raise AssertionError(
            f"previous command failed with {ret}, {stdout=}, {stderr=}"
        )


def run_in_context(context, cmd: list[str], can_fail: bool = False, **run_args):
    check_context_exit_code(context)

    context.cmd = cmd

    if hasattr(context, "working_dir") and "cwd" not in run_args:
        run_args["cwd"] = context.working_dir

    if env := getattr(context, "env", None):
        run_args["env"] = {**env, **run_args.get("env", {})}

    context.ret, context.stdout, context.stderr = run(cmd, **run_args)

    if not can_fail:
        check_context_exit_code(context)


@behave.step('I create a tea config for the user "{user}" using token "{token}"')
def step_impl(context, user: str, token: str) -> None:
    user = user.format(context=context)
    token = token.format(context=context)

    if not (conf_home := getattr(context, "xdg_config_home_dir", None)):
        raise RuntimeError("context.xdg_config_home_dir must be set")

    (tea_conf_dir := (Path(conf_home.name) / "tea")).mkdir(parents=True, exist_ok=True)
    with open(str(tea_conf_dir / "config.yml"), "w") as tea_conf_file:
        tea_conf_file.write(
            f"""---
logins:
- name: src.opensuse.org
  url: https://src.opensuse.org
  token: {token}
  default: false
  ssh_host: src.opensuse.org
  ssh_key: ""
  insecure: false
  user: {user}
  created: {int(time.time())}
preferences:
  editor: false
  flag_defaults:
    remote: ""
"""
        )


@behave.step('I set the working directory to "{path}"')
def step_impl(context, path: str) -> None:
    path = path.format(context=context)
    context.working_dir = path


@behave.step('stdout contains "{text}"')
def step_impl(context, text: str):
    if re.search(text := text.format(context=context), context.stdout):
        return
    raise AssertionError(f"Stdout doesn't contain expected pattern: {text}")


@behave.step("stdout is")
def step_impl(context):
    expected = context.text.format(context=context).rstrip().split("\n")
    found = context.stdout.rstrip().split("\n")

    if found == expected:
        return

    raise AssertionError(
        """Stdout is not:
"""
        + "\n".join(expected)
        + """

Actual stdout:
"""
        + "\n".join(found)
        + """
"""
    )


@behave.step("stderr is")
def step_impl(context):
    expected = context.text.format(context=context).rstrip().split("\n")
    found = context.stderr.rstrip().split("\n")

    if found == expected:
        return

    raise AssertionError(
        """stderr is not:
"""
        + "\n".join(expected)
        + """

Actual stderr:
"""
        + "\n".join(found)
        + """
"""
    )


@behave.step("a checked out copy of trivy")
def step_impl(context):
    ret, _, _ = run(
        shlex.split(f"{context.osc} checkout Virtualization:containers/trivy")
    )
    assert ret == 0


@behave.step('I run "{cmd}"')
def i_run(context, cmd: str) -> None:
    cmd = cmd.format(context=context)
    check_context_exit_code(context)

    run_in_context(context, shlex.split(cmd))


@behave.step('I run osc "{cmd}"')
def i_run_osc(context, cmd: str) -> None:
    cmd = cmd.format(context=context)
    check_context_exit_code(context)

    run_in_context(context, shlex.split(f"{context.osc} {cmd}"))

    if "fork" in (cmd_s := cmd.split()) and "delete" not in cmd_s:
        pkg_name = os.path.basename(getattr(context, "working_dir", os.getcwd()))
        forks = getattr(context, "forks", [])
        forks.append(pkg_name)
        context.forks = forks
