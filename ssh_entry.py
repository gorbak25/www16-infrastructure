#!/usr/bin/env python3
import os
import datetime
import shlex
import json
import hmac
import locale
import string
import random
import stat
from contextlib import contextmanager
import pyzfscmds.cmd
import pyzfscmds.utility

from config import *

this_dir = os.path.dirname(os.path.abspath(__file__))

try:
    authorized = json.loads(open(os.path.join(this_dir, AUTH_FILENAME), "rb").read())
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
        formated_time: string = dt.strftime("%Y-%m-%d-%H-%f")
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
    Puts the given pubkey to /home/user/.ssh/authorized_keys
    It might be a good idea to snapshot your container before doing this!
    Example:
    ssh www16@gorbak25.eu authorize_key \'ssh-rsa AAAAB3Nz...CmNiJU= gorbak25@ra.cc\'
    """)
    exit(0)

def does_clone_exist(dataset):
    if pyzfscmds.utility.dataset_exists(dataset):
        return True
    try:
        if pyzfscmds.utility.is_clone(dataset):
            return True
        else:
            return False
    except:
        return False

def create_rootfs(base_dataset, client_dataset, client_dataset_mountpath):
    # Ok the dataset is gone, Time to create a new clone
    s = ''.join(random.choices(string.ascii_uppercase, k=16))
    pyzfscmds.cmd.zfs_snapshot(base_dataset, s)
    try:
        pyzfscmds.cmd.zfs_clone(f"{base_dataset}@{s}", client_dataset,
                                properties=[f"mountpoint={client_dataset_mountpath}"])
    finally:
        # Mark the snapshot for deletion so when the clone is destroyed this will get nuked
        pyzfscmds.cmd.zfs_destroy_snapshot(f"{base_dataset}@{s}", defer=True)
    print("Created a fresh ROOTFS just for you\n*raccoon noises*")

def banhammer(user):
    print("You angried a raccoon...")
    # TODO: ban the guy who tried to escape from the container via the oldest trick in the book...
    exit(0)

def render_deployment_template(user, user_rootfs):
    template = open(os.join(this_dir, "k8s/www16-user.yaml.template"), "r").read()
    return template.replate("$WWW_USER", user).replace("$WWW_USER_ROOTFS", user_rootfs)

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

print("Authorized!")

# Common variables usefull for commands
client_dataset = os.path.join(DATASET_CONTAINER_ROOT, DATASET_CLIENT_NAME, user)
client_dataset_mountpath = os.path.join(DATASET_CLEINT_MOUNT, user)
base_dataset = os.path.join(DATASET_CONTAINER_ROOT, DATASET_BASE_NAME)

if cmd == "start":
    if not does_clone_exist(client_dataset):
        create_rootfs(base_dataset, client_dataset, client_dataset_mountpath)

    # Ok we got the rootfs - render the deployment template and push it to the k8s apiserver
    deployment_spec = render_deployment_template(user, client_dataset_mountpath)
    print(deployment_spec)

elif cmd == "list_snapshots":
    try:
        snap = pyzfscmds.cmd.zfs_list(client_dataset, zfs_types=["snapshot"], columns=['name']).splitlines()
    except:
        snap = []
    snap = map(lambda x: x.split("@")[1], snap)[::-1]

    print("Current snapshots of your container:")
    for s in snap:
        print(f"* {s}")
    print("* BASE")
    print("")
    print("You may rollback at any time. REMEMBER THAT ROLLING BACK IS PERMANENT!!!")
    print("Don't cry like a baby if you accidentally nuked your container...")
    print("It my be a good idea to stop your container before rolling back your rootfs")
    print("Rolling back to BASE always creates a fresh rootfs")

elif cmd == "snapshot":
    if does_clone_exist(client_dataset):
        try:
            pyzfscmds.cmd.zfs_snapshot(client_dataset, format_datetime(datetime.datetime.now()))
            print("Created a snapshot of your container!")
        except:
            print("Failed to snapshot your container")
    else:
        print("You must start your container at least once in order to snapshot!")

elif cmd == "rollback":
    if len(args) != 4:
        print("Please provide a snapshot id!")
        exit(0)

    to = args[3]
    try:
        if to != "BASE":
            parse_time(to)
    except:
        print("*confused raccoon noises*")
        exit(0)

    if to != "BASE":
        client_dataset_snapshot = f"{os.path.join(DATASET_CONTAINER_ROOT, DATASET_CLIENT_NAME, user)}@{to}"
        try:
            pyzfscmds.cmd.zfs_rollback(client_dataset_snapshot, destroy_between = True)
            print(f"Rolled back to {to}")
        except:
            print("Failed to rollback :( Perhaps stop the container first?")
    else:
        # Try to delete the client dataset
        try:
            pyzfscmds.cmd.zfs_destroy(client_dataset, verbose = True, recursive_children = True)
        except Exception as ex:
            print(f"Warning: Failed to delete {client_dataset}")
            print(ex)

        if does_clone_exist(client_dataset):
            print("Error: rootfs exists and couldn't be deleted")
        else:
            create_rootfs(base_dataset, client_dataset, client_dataset_mountpath)

elif cmd == "authorize_key":
    if len(args) != 4:
        print("Please provide a public key!")
        exit(0)

    client_keydata = args[3]
    client_dataset_key_file = os.path.join(client_dataset_mountpath, "home/user/.ssh/authorized_keys")
    if not does_clone_exist(client_dataset):
        print("You must start your container at least once to do this!")
        exit(0)

    # Prepare for some posix bullshit...
    lstat_info = os.lstat(client_dataset_key_file)
    fd = os.open(path, os.O_RDWR)
    fstat_info = os.fstat(fd)
    if lstat_info.st_mode != fstat_info.st_mode:
        banhammer(user)
    if lstat_info.st_ino != fstat_info.st_ino:
        banhammer(user)
    if lstat_info.st_dev != fstat_info.st_dev:
        banhammer(user)
    if not stat.S_ISREG(lstat_info.st_mode):
        banhammer(user)

    os.write(fd, client_keydata)
    os.close(fd)

else:
    print("No such command!")
exit(0)
