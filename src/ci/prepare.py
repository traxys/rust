#!/usr/bin/env python3

import io
import os
import re
import subprocess

def run(b):
    b.step("dump-environment.sh", "Show the current environment")
    b.step("install-sccache.sh", "Install sccache")
    b.step("install-clang.sh", "Install clang")
    b.step("switch-xcode.sh", "Switch to Xcode 9.3")
    b.step("install-wix.sh", "Install WIX")
    b.step("install-innosetup.sh", "Install InnoSetup")
    b.step(
        "windows-symlink-build-dir.sh",
        "Ensure the build happens on C:\\ instead of D:\\",
    )
    b.step(
        "disable-git-crlf-conversion.sh",
        "Disable git automatic line ending conversion (on C:\\)",
    )
    b.step("install-msys2.sh", "Install msys2")
    b.step("install-mingw.sh", "Install MinGW")
    b.step("install-ninja.sh", "Install ninja")
    b.step("enable-docker-ipv6.sh", "Enable IPv6 on Docker")

    # Disable automatic line ending conversion (again). On Windows, when we're
    # installing dependencies, something switches the git configuration directory or
    # re-enables autocrlf. We've not tracked down the exact cause -- and there may
    # be multiple -- but this should ensure submodules are checked out with the
    # appropriate line endings.
    b.step(
        "disable-git-crlf-conversion.sh",
        "Disable git automatic line ending conversion",
    )

    b.step("checkout-submodules.sh", "Checkout submodules")
    b.step("verify-line-endings.sh", "Verify line endings")
    b.step("install-awscli.sh", "Install awscli")

LOG_COMMAND_ADD_PATH_RE = re.compile(r"^##vso\[task\.prependpath\](.*)$")
LOG_COMMAND_SET_ENV_RE = re.compile(
    r"^##vso\[task\.setvariable variable=([0-9A-Za-z_]+)\](.*)$"
)

class Build:
    def __init__(self):
        self.env = dict(os.environ)

    def step(self, script, name):
        print("==== %s ====" % name)

        # While the scripts can be executed mostly as-is, they emit log
        # commands understood by the CI agent. Some of those commands (such as
        # setting new environment variables and adding items to the path) need
        # to be executed in order for the following scripts to succeed, so we
        # read the process output line by line and emulate them.
        path = os.path.join(os.path.dirname(__file__), "scripts", script)
        proc = subprocess.Popen(
            [path],
            env=self.env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        for line in io.TextIOWrapper(proc.stdout, encoding="utf-8"):
            self.handle_log_commands(line)
            print(line, end="")
        proc.wait()

        if proc.returncode != 0:
            print("==== failure: %s ====" % name)
            print("exit code: %s" % proc.returncode)
            exit(proc.returncode)
        else:
            print("==== success: %s ====" % name)
        print()

    def handle_log_commands(self, line):
        if not line.startswith("##vso["):
            return

        add_path = LOG_COMMAND_ADD_PATH_RE.match(line)
        set_env = LOG_COMMAND_SET_ENV_RE.match(line)
        if add_path is not None:
            self.env["PATH"] = add_path.group(1) + ":" + self.env["PATH"]
        elif set_env is not None:
            self.env[set_env.group(1)] = set_env.group(2)
        else:
            print("ERROR: src/ci/prepare.py: unsupported log command: " + line)
            exit(1)

if __name__ == "__main__":
    run(Build())
