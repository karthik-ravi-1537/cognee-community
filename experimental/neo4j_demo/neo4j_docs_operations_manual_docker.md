----- https://neo4j.com/docs/operations-manual/current/docker/introduction/ -----

# Getting started with Neo4j in Docker
Docker can be downloaded for macOS, Windows, and Linux operating systems from https://www.docker.com/get-started. DockerHub hosts an official Neo4j image that provides a standard, ready-to-run package of Neo4j Community Edition and Enterprise Edition for a variety of versions.

## Getting the Neo4j image
Variants of the Neo4j image are tagged according to Community/Enterprise Edition and the operating system used as the base image.

### Neo4j editions
Tags are available for both Community Edition and Enterprise Edition. Version-specific Enterprise Edition tags have an -enterprise suffix after the version number, for example: neo4j:2025.05.0-enterprise. Community Edition tags have no suffix, for example neo4j:2025.05.0. The latest Neo4j Enterprise Edition release is available as neo4j:enterprise.

Neo4j Enterprise Edition license
To use Neo4j Enterprise Edition, you must accept the license agreement by setting the environment variable NEO4J_ACCEPT_LICENSE_AGREEMENT=yes.

© Network Engine for Objects in Lund AB. 2023. All Rights Reserved. Use of this Software without a proper commercial license with Neo4j, Inc. or its affiliates is prohibited.

Email inquiries can be sent using the form Contact Neo4j.

More information is also available at: https://neo4j.com/licensing/

### Base operating system
The Neo4j image is available with either debian:bullseye-slim or redhat/ubi9-minimal:latest as the base image. The default is debian:bullseye-slim.

If you are unsure which base image to use or have no preference, just use the default of neo4j:2025.05.0.

To specify which base image to use, the image tags optionally have a -bullseye or -ubi9 suffix.

For example:

neo4j:2025.05.0-bullseye            # debian 11 community
neo4j:2025.05.0-enterprise-bullseye # debian 11 enterprise
neo4j:2025.05.0-ubi9              # redhat UBI9 community
neo4j:2025.05.0-enterprise-ubi9   # redhat UBI9 enterprise
neo4j:2025.05.0                   # debian 11 community
neo4j:2025.05.0-enterprise        # debian 11 enterprise
Table 1. Base images and the corresponding tag suffix.
tag suffix	Base Image
-bullseye

debian:bullseye-slim

-ubi9

redhat/ubi9-minimal:latest

unspecified

debian:bullseye-slim

The Red Hat UBI9 variant images are only available from 5.17.0 and onwards. For earlier Neo4j versions, do not specify a base image.

## Using the Neo4j Docker image
You can start a Neo4j container by using the following command. Note that this Neo4j container will not persist data between restarts and will have the default username/password.

docker run \
    --restart always \
    --publish=7474:7474 --publish=7687:7687 \
    neo4j:2025.05.0
You can try out your Neo4j container by opening http://localhost:7474/ (the Neo4j’s Browser interface) in a web browser. By default, Neo4j requires authentication and prompts you to log in with a username/password of neo4j/neo4j at the first connection. You are then prompted to set a new password.

The default minimum password length is 8 characters.

Use the dbms.security.auth_minimum_password_length configuration setting to change the default minimum value.

The following sections provide more information about how to set an initial password, configure Neo4j to persist data between restarts, and use the Neo4j Docker image.

## Persisting data between restarts
The --volume option maps a local folder to the container, where you can persist data between restarts. To persist the contents of the database between containers, mount a volume to the /data directory on starting the container:

docker run \
    --restart always \
    --publish=7474:7474 --publish=7687:7687 \
    --env NEO4J_AUTH=neo4j/your_password \
    --volume=/path/to/your/data:/data \
    neo4j:2025.05.0
The folders that you want to mount must exist before starting Docker, otherwise, Neo4j fails to start due to permissions errors.

For more information about mounting volumes, see Persisting data with Docker volumes.

## Using NEO4J_AUTH to set an initial password
When using Neo4j in a Docker container, you can set the initial password for the database directly by specifying the NEO4J_AUTH in your run directive:

docker run \
    --restart always \
    --publish=7474:7474 --publish=7687:7687 \
    --env NEO4J_AUTH=neo4j/your_password \
    neo4j:2025.05.0
Alternatively, you can disable authentication by specifying NEO4J_AUTH to none:

--env NEO4J_AUTH=none
Note that there is currently no way to change the initial username from neo4j.

Setting NEO4J_AUTH does not override the existing authentication.

If you have mounted a /data volume containing an existing database, setting NEO4J_AUTH will have no effect because that database already has authentication configured. The Neo4j Docker service will start, but you will need a username and password already associated with the database to log in.

## Useful docker run options
This table lists some of the options available:

Table 2. Options for docker run
Option	Description	Example
--name

Name your container to avoid generic ID.

docker run --name myneo4j neo4j

-p

Specify which container port to expose.

docker run -p7687:7687 neo4j

-d

Detach container to run in the background.

docker run -d neo4j

-v

Bind mount a volume.

docker run -v $HOME/neo4j/data:/data neo4j

--env

Set config as environment variables for the Neo4j database.

docker run --env NEO4J_AUTH=neo4j/your_password neo4j

--user

Run neo4j as the given user, instead of neo4j.

docker run --user="$(id -u):$(id -g)" neo4j

--restart

Control whether Neo4j containers start automatically when they exit, or when Docker restarts.

docker run --restart always

--help

Output full list of docker run options

docker run --help

The --restart always option sets the Neo4j container (and Neo4j) to restart automatically whenever the Docker daemon is restarted.

If you no longer want to have the container auto-start on machine boot, you can disable this setting using the flag no, for example, docker update --restart=no <containerID>.
For more information on Docker restart policies, see the official Docker documentation.

## Offline installation of Neo4j Docker image
Docker provides the docker save command for downloading an image into a .tar package so that it can be used offline, or transferred to a machine without internet access.

This is an example command to save the neo4j:2025.05.0 image to a .tar file:

docker save -o neo4j-2025.05.0.tar neo4j:2025.05.0
To load a docker image from a .tar file created by docker save, use the docker load command. For example:

docker load --input neo4j-2025.05.0.tar
For complete instructions on using the docker save and docker load commands, refer to:

The official docker save documentation.

The official docker load documentation.