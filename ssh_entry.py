#!/usr/bin/env python3
import os
import datetime
import shlex
import json
import hmac
from contextlib import contextmanager
import pyzfscmds.cmd
import pyzfscmds.utility

from config import *

try:
    authorized = json.loads(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), AUTH_FILENAME), "rb").read())
except:
    print("Tool broken. Contact the raccoon :P")
    exit(0)

@contextmanager
def setlocale(encoding: str = "C"):
    """
    See: https://stackoverflow.com/a/24070673
    """
    saved = locale.setlocale(locale.LC_ALL)
    try:
        yield locale.setlocale(locale.LC_ALL, encoding)
    finally:
        locale.setlocale(locale.LC_ALL, saved)

def parse_time(origin_property: str, fmt: str = "%Y-%m-%d-%H-%f",
               encoding: str = "C", no_setlocale: bool = False) -> datetime:
    if no_setlocale:
        return datetime.datetime.strptime(origin_property, fmt)

    with setlocale(encoding=encoding):
        origin_datetime: datetime = datetime.datetime.strptime(origin_property, fmt)
    return origin_datetime

def format_datetime(dt):
    with setlocale():
        formated_time: string = dt.strftime(snap_suffix_time_format)
    return formated_time

def help():
    print("""
    Welcome to the management interface of the WWW docker service!
    If you are explicitly whitelisted by the admin then you may
    get your own publicly visible docker container and manage it via this interface!

    Use this interface only for the initial setup of ssh to the 
    container, managing backups/snapshots and querying status information.
    The admin should have provided you with an openvpn profile for
    connecting to the appropriate network where you may access your container.

    Usage:
    ssh www16@gorbak25.eu username token [COMMAND]
    Where username and token were provided to you by the admin and command is one of:
    - start
    Starts your container if not already started.
    
    - stop
    Stops your container.
    
    - status
    Gets the status information of your container
    
    - list_snapshots
    Lists snapshots of your container
    
    - snapshot
    Snapshots your container
    
    - rollback [snapshot_id]
    Rollbacks your container to the given id
    
    - expose [your_prefix]
    Redirects http traffic from your_prefix.gorbak25.eu to your container on port 80
    
    - hide
    Stops traffic from your_prefix.gorbak25.eu from reaching you
    
    - authorize_key [ssh-pubkey]
    Puts the given data to /home/user/.ssh/authorized_keys
    Remember to snapshot your container before doing this!
    Example:
    ssh www16@gorbak25.eu authorize_key \'ssh-rsa AAAAB3Nz...CmNiJU= gorbak25@ra.cc\'
    """)
    exit(0)

if 'SSH_ORIGINAL_COMMAND' not in os.environ:
    help()

args = shlex.split(os.environ['SSH_ORIGINAL_COMMAND'])
if len(args) < 3 or len(args) > 4:
    help()

user = args[0]
token = args[1]
cmd =  args[2]

if user not in authorized:
    print("No such user!")
    exit(0)

if not hmac.compare_digest(token, authorized[user]):
    print("Invalid token!")
    exit(0)

if cmd == "list_snapshots":
    try:
        snap = pyzfscmds.cmd.zfs_list(os.path.join(DATASET_CONTAINER_ROOT, DATASET_CLIENT_NAME, user), zfs_types=["snapshot"])
    except:
        snap = []
    snap = map(lambda x: x.split("@")[1], snap)

    print("Current snapshots of your container:")
    for s in snap:
        print(f"* {s}")
    print("* BASE")
    print("")
    print("You may rollback at any time. REMEMBER THAT ROLLING BACK IS PERMANENT!!!")
    print("Don't cry like a baby if you accidentally nuked your container...")
    print("It my be a good idea to stop your container before rolling back your rootfs")

elif cmd == "snapshot":
    client_dataset = os.path.join(DATASET_CONTAINER_ROOT, DATASET_CLIENT_NAME, user)
    if not pyzfscmds.utility.dataset_exists(client_dataset):
        is_clone = None
        try:
            is_clone = pyzfscmds.utility.is_clone(client_dataset)
        except:
            pass
        if not is_clone:
            print("You must start your container at least once in order to snapshot!")
            exit(0)

    # Ok the client dataset exists - snapshot it :3
    try:
        pyzfscmds.cmd.zfs_snapshot(client_dataset, format_datetime(datetime.datetime.now()))
        print("Created a snapshot of your container!")
    except:
        print("Failed to snapshot your container")

elif cmd == "rollback":
    if len(args) != 4:
        print("Please provide a snapshot id!")
        exit(0)

    to = args[3]
    try:
        if to != "BASE":
            parse_time(to)
    except:
        print("*angry raccoon noises*")
        exit(0)

    if to != "BASE":
        client_dataset = f"{os.path.join(DATASET_CONTAINER_ROOT, DATASET_CLIENT_NAME, user)}@{to}"
        try:
            pyzfscmds.cmd.zfs_rollback(client_dataset)
            print(f"Rolled back to {to}")
        except:
            print("Failed to rollback :( Perhaps stop the container first?")
    else:
        client_dataset = os.path.join(DATASET_CONTAINER_ROOT, DATASET_CLIENT_NAME, user)
        client_dataset_mountpath = os.path.join(DATASET_CLEINT_MOUNT, user)
        base_dataset = os.path.join(DATASET_CONTAINER_ROOT, DATASET_BASE_NAME)
        # Try to delete the client dataset
        try:
            pyzfscmds.cmd.zfs_destroy(client_dataset, verbose=True)
        except Exception as ex:
            print(f"Warning: Failed to delete {client_dataset}")
            print(ex)

        # Ensure it does not exist
        if pyzfscmds.utility.dataset_exists(client_dataset):
            print("Error: dataset exists")
            exit(0)
        try:
            if pyzfscmds.utility.is_clone(client_dataset):
                print("Error: dataset exists")
                exit(0)
        except:
            pass

        # Ok the dataset is gone, Time to create a new clone
        s = format_datetime(datetime.datetime.now())
        pyzfscmds.cmd.zfs_snapshot(base_dataset, s)
        pyzfscmds.cmd.zfs_clone(f"{base_dataset}@{s}", client_dataset, properties=[f"mountpoint={client_dataset_mountpath}"])
        print("Created a fresh ROOTFS just for you *raccoon noises*")
else:
    print("No such command!")
exit(0)
