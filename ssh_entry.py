#!/usr/bin/env python3
import os

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
    - status
    Gets the status information of your container
    - kill
    Kills your container.
    - start
    Starts your container if not already started.
    - list_snapshots
    Lists snapshots of your container
    - snapshot
    Snapshots your container
    - rollback [snapshot_id]
    Rollbacks your container to the given id
    - expose [prefix]
    Redirects http traffic from prefix.gorbak25.eu to your container on port 80
    """)
    exit(0)

if 'SSH_ORIGINAL_COMMAND' not in os.environ:
    help()

args = [e for e in os.environ['SSH_ORIGINAL_COMMAND'].split(' ') if len(e)>0]
if len(args) < 3 or len(args) > 4:
    help()

print(args)

