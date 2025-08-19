----- https://neo4j.com/docs/operations-manual/current/introduction/ -----

# Introduction

Neo4j is the world’s leading graph database. The architecture is designed for optimal management, storage, and traversal of nodes and relationships. The graph database takes a property graph approach, which is beneficial for both traversal performance and operations runtime. Neo4j offers dedicated memory management and memory-efficient operations.

Neo4j is scalable and can be deployed as a standalone server or across multiple machines in a fault-tolerant cluster for production environments. Other features for production applications include hot backups and extensive monitoring.

## Neo4j editions
There are two editions of self-managed Neo4j to choose from, the Community Edition (CE) and the Enterprise Edition (EE). The Enterprise Edition includes all that Community Edition offers, plus extra enterprise requirements such as backups, clustering, and failover capabilities.

Community Edition
The Community Edition is a fully functional edition of Neo4j, suitable for single-instance deployments. It fully supports key Neo4j features, such as ACID-compliant transactions, Cypher, and programming APIs. It is ideal for learning Neo4j, do-it-yourself projects, and applications in small workgroups.

Enterprise Edition
The Enterprise Edition extends the functionality of Community Edition to include key features for performance and scalability, such as a clustering architecture and online backup functionality. Additional security features include role-based access control and LDAP support, for example, Active Directory. It is the choice for production systems with requirements for scale and availability, such as commercial and critical internal solutions.


----- https://neo4j.com/docs/operations-manual/current/installation/ -----

# Installation

Neo4j can be installed in different deployment contexts, such as Linux, macOS, and Windows.

The following topics are covered:

System requirements — The system requirements for a production deployment of Neo4j.

Linux — Installation instructions for Linux.

macOS — Installation instructions for macOS.

Windows — Installation instructions for Windows.

Neo4j Desktop — About Neo4j Desktop.

TIP: Installation-free options
Neo4j AuraDB is a fully managed Neo4j database, hosted in the cloud and requires no installation. For more information, see the AuraDB product page and AuraDB documentation.

Neo4j can be run in a Docker container. For information on running Neo4j on Docker, see Docker.

----- https://neo4j.com/docs/operations-manual/current/installation/requirements/ -----

# System requirements

Neo4j can be installed in many environments and for different scopes, therefore system requirements largely depend on the use of the software. This section distinguishes between a personal/development installation and a server-based installation used for production workloads.

Neo4j AuraDB is a fully managed Neo4j database, hosted in the cloud and requires no installation. For more information, see the AuraDB product page and AuraDB documentation.

## Supported platforms
Neo4j is supported on systems with x86_64 and ARM architectures on physical, virtual, or containerized platforms.

## Hardware requirements
In terms of minimum hardware requirements, follow these guidelines:

Table 1. Hardware requirement guidelines
CPU

Performance is generally memory or I/O bound for large graphs, and compute-bound for graphs that fit in memory.

Memory

More memory allows for larger graphs, but it needs to be configured properly to avoid disruptive garbage collection operations.

Storage

Aside from capacity, the performance characteristics of the disk are the most important when selecting storage:

Neo4j workloads tend significantly toward random reads.

Select media with low average seek time: SSD over spinning disks.

For personal use and software development:

Table 2. Hardware requirement guidelines for personal use and software development
CPU

Intel x86-x64 Core i3 minimum, Core i7 recommended. AMD x86-x64, Mac ARM.

Memory

2GB minimum, 16GB or more recommended.

Storage

10GB SATA Minimum, SSD with SATA Express or NVMe recommended.

For cloud environments:

Table 3. Hardware requirement guidelines for cloud environments
CPU

2vCPU minimum, 16+ recommended.

Memory

2GB minimum. Actual requirements depend on workloads. In some cases, it is recommended to use instances with memory that fits the size of the graph in use.

Storage

10GB minimum block storage, attached NVMe SSD recommended. Storage size depends on the size of the databases.

For server-based, on-premise environments:

Table 4. Hardware requirement guidelines for server-based, on-premise environments
CPU

Intel/AMD x86-x64. ARM64.

Memory

8GB minimum. Actual requirements depend on workloads. In some cases, it is recommended to use instances with memory that fits the size of the graph in use.

Storage

RAID/SAN or SSD with greater than 5000 IOPS. NVMe SSD is recommended. Storage size depends on the size of the databases.

For more information, see Performance, and more specifically Memory Configuration and Tuning of the garbage collector, and Disks, RAM and other tips.

## Software requirements
For personal use and software development:

Table 5. Software requirements for personal use and software development
Operating System	Supported JDK
Debian 11, 12

OpenJDK 21, OracleJDK 21, and ZuluJDK 21

MacOS 13, 14, 15

OpenJDK 21, ZuluJDK 21

SuSE Enterprise Desktop 15

OpenJDK 21, OracleJDK 21

Ubuntu Desktop 22.04, 24.04

OpenJDK 21, OracleJDK 21, and ZuluJDK 21

Windows 11

OracleJDK 21, ZuluJDK 21

For cloud environments, and server-based, on-premise environments:

Table 6. Software requirements for cloud environments, and server-based, on-premise environments
Operating System	Supported JDK
Amazon Linux 2023 AMI

Amazon Corretto 21, and OracleJDK 21

CentOS Stream 8, 9

OpenJDK 21, OracleJDK 21, and ZuluJDK 21

Debian 11, 12

OpenJDK 21, OracleJDK 21, and ZuluJDK 21

Red Hat Enterprise Linux Server 8.10, 9.2, 9.4, 9.6

Red Hat OpenJDK 21, Oracle JDK 21, and ZuluJDK 21

Ubuntu Server 22.04, 24.04

OpenJDK 21, OracleJDK 21, and ZuluJDK 21

Windows Server 2022, 2025

OracleJDK 21, ZuluJDK 21

For more information on Red Hat Enterprise Linux Life Cycle, refer to their official documentation.

## Filesystem
For proper ACID behavior, the filesystem must support flush (fsync, fdatasync). Since databases can put a high and consistent load on a storage system for a long time, it is recommended to use a file system that has good aging characteristics. The EXT4 and XFS are the only supported file systems.

See Linux file system tuning for details on how to configure the filesystem in Linux for optimal performance.

If tmp is set to noexec, it is recommended to set server.jvm.additional=-Djava.io.tmpdir=/home/neo4j in conf/neo4j.conf and replace /home/neo4j with a path that has exec permissions.

For /bin/cypher-shell, set this via an environment variable: export JAVA_OPTS=-Djava.io.tmpdir=/home/neo4j and replace /home/neo4j with a path that has exec permissions.

For the Neo4j’s uses of the Java Native Access (JNA) library, set server.jvm.additional=-Djna.tmpdir=/tmp in conf/neo4j.conf and replace /tmp with a path that has exec permissions.

## Java
It is required to have a pre-installed, compatible Java Virtual Machine (JVM) to run a Neo4j instance. The minimum requirement is Java Runtime Environment (JRE).

Table 7. Neo4j version and JVM requirements
Neo4j Version	JVM compliancy
2025.01

Java SE 21 Platform Specification

5.26 LTS

Java SE 17 and Java SE 21 Platform Specification

5.14

Java SE 17 and Java SE 21 Platform Specification

5.x

Java SE 17 Platform Specification

4.x

Java SE 11 Platform Specification

3.x

Java SE 8 Platform Specification

Neo4j Desktop is available for developers and personal users. Neo4j Desktop is bundled with a JVM. For more information on how to use Neo4j Desktop and its capabilities, see the Neo4j Desktop documentation.

----- https://neo4j.com/docs/operations-manual/current/installation/linux/ -----

# Linux installation

You can install Neo4j on Linux using Debian or RPM packages, or from a Tar archive.

----- https://neo4j.com/docs/operations-manual/current/installation/osx/ -----

# macOS installation

Before you install Neo4j on macOS, check System Requirements to see if your setup is suitable.

## Unix console application

## macOS service
Use the standard macOS system tools to create a service based on the neo4j command.

## macOS file descriptor limits

----- https://neo4j.com/docs/operations-manual/current/installation/windows/ -----

# Windows installation

Before you install Neo4j on Windows, check System Requirements to see if your setup is suitable.

## Windows console application


## Windows service

Neo4j can also be run as a Windows service.


## Windows PowerShell module
The Neo4j PowerShell module allows administrators to:

Install, start, and stop Neo4j Windows® Services.

Start tools, such as Neo4j Admin and Cypher Shell.

The PowerShell module is installed as part of the ZIP file distributions of Neo4j.

----- https://neo4j.com/docs/operations-manual/current/installation/neo4j-desktop/ -----

# Neo4j Desktop

Neo4j Desktop is a convenient way for developers to work with local Neo4j databases.

Neo4j Desktop is not suited for production environments.

To install Neo4j Desktop, go to Neo4j Deployment Center and follow the instructions.

