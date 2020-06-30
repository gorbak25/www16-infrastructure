
# json file with authorized external users
AUTH_FILENAME = "authorized.json"

# zfs dataset where all the stuff lies
DATASET_CONTAINER_ROOT = "vault/DATA/WWW16-INFRASTRUCTURE/USER-CONTAINERS"

# the base image of which all containers are based off
DATASET_BASE_MOUNT = "/home/www16/user-containers/base"
DATASET_BASE_NAME = "base"

# All client containers are children of this
DATASET_CLEINT_MOUNT = "/home/www16/user-containers/clients"
DATASET_CLIENT_NAME = "CLIENTS"
