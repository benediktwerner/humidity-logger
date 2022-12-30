#!/usr/bin/env python3

import os, sys

args = sys.argv[1:]

SERVICE_ARGS = ("-s", "--service")
RESTART_ARGS = ("-r", "--restart")
ARGS = SERVICE_ARGS + RESTART_ARGS
DIRECTORY = "~/humidity-logger/"

if len(args) == 0 or any(a not in ARGS for a in args[1:]) or args[0].startswith("-"):
    print(
        "Usage:",
        sys.argv[0],
        "HOSTNAME",
        *("[" + "|".join(a) + "]" for a in (SERVICE_ARGS, RESTART_ARGS)),
    )

host, *args = args
host = f"wernerfamily@{host}"

print("Connecting to", host)


def ssh(cmd):
    os.system(f"ssh {host} '{cmd}'")


def scp(file):
    os.system(f"scp {file} {host}:{DIRECTORY}")


def sudo_scp(file, target):
    scp(file)
    ssh(f"sudo mv {DIRECTORY}/{file} {target}")


ssh(f"mkdir -p {DIRECTORY}")
scp("logger.py")

if any(s in args for s in SERVICE_ARGS):
    sudo_scp("humidity-logger.service", "/etc/systemd/system/")


if any(s in args for s in RESTART_ARGS):
    ssh("sudo systemctl restart humidity-logger")
