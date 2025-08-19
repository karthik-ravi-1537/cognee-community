----- https://neo4j.com/docs/aura/ -----

# Neo4j Aura Documentation


Neo4j Aura is a fully automated graph platform offered as a cloud service. It brings together the capabilties of several tools, services, and operations from the Neo4j catalog. To get started with Neo4j Aura, log in at https://console-preview.neo4j.io/account/profile, or click "Get Started Free" at the top of the page.

The Neo4j Aura console, or console for short, is the new UI experience for Neo4j Aura users. Use the console to import and interact with your data — from visualizing nodes and relationships to executing queries with the Cypher query language. You can monitor your instances and databases via metrics and logs to get insight into various aspects, such as performance, resource usage, and overall system health.

The Aura environment starts with an organization which can contain multiple projects with multiple users associated. Projects, users, and billing can all be managed directly from the same console.

If you have used Aura before, you will find the console familiar but with a host of new features. The classic Aura console is still available, and will remain available until all available features have been integrated into the new console.

See New Neo4j Aura console for a comparison between the new console and the classic experience.

Aura includes AuraDB, a fully managed graph database, and AuraDS, a fully managed data science as a service solution for running graph analytics on Aura. The documentation is based on AuraDB unless specified otherwise. See Graph analytics in Aura for more information about AuraDS and graph analytics.

Plans
Aura offers the following subscription plans:

AuraDB Free

AuraDB Professional

AuraDB Business Critical

AuraDB Virtual Dedicated Cloud

AuraDS Professional

AuraDS Enterprise

----- https://neo4j.com/docs/aura/new-console/ -----

# New Neo4j Aura console
The new console is an evolution of the classic Aura console, updated to enhance the experience with Neo4j Aura. It integrates the features and functionalities of various tools, services, and operations from the Neo4j catalog.

The key features, structural changes, and improvements compared to the classic console are outlined here.

## What’s new

### Key features and improvements

Vector-optimized configurations - Optimized for AI workloads, enabling more efficient use of graph data. See Vector optimization for more information.

Graph Analytics plugin - Allows you to experiment with graph algorithms within the console. See Graph Analytics plugin for more information.

Secondaries - Scale the read query workload of your AuraDB instance while maintaining high availablility. See Secondaries for more information.

Database import/restore - Upload and restore databases from multiple data sources, including support for PostgreSQL, MySQL, SQL Server, Oracle, as well as local .CSV files. See Import for more information.

Billing - The interface has been redesigned to be easier to navigate and more transparent.

### Navigation updates
More streamlined access to instance details - Connection status, instance configuration, metrics, and more are available from the instance card. See Instance details for more information.

A unified navigation bar - Allows you to quickly switch between tools like Query and Explore, to Settings and User management, for example. See Visual tour for more information about the UI.

### Topology
Organization

Centralized management of settings and roles, supporting improved scaling and governance.

Organization owner - A new role that allows shared administrative responsibility.

OAuth (SSO) - Configurable single sign-on for secure and simplified authentication.

Project is the evolution of Tenant.

Projects allow you to organize multiple instances under a single project to standardize configurations and streamline access control.

You can assign project-specific roles to manage permissions effectively. See User management for more information.

Instance

Improved instance management - You can now resize instances, monitor monthly usage, and manage custom endpoints directly from the instance card.

Rolling updates - Updates are applied without downtime with optional deferred updates for production environments.

### Integrated tools
Query and Explore are tools for querying and visualizing your data and are now integrated into the console. You can navigate between instances directly from the tools.

### Assisted querying
Cypher reference - Available directly in the Query tool.

Co-pilots - Allows you to use natural language to query the database. Co-pilots are available both in the Query and Explore tools.

### Connectivity
Auto-connect - Establish connections to your database automatically.

Database user connections - Support for connecting using database credentials.

Remote connections - Allows you to connect from remote sources.

Cloud metadata storage - Centralized repository for queries, visualization scenes, and configurations.

### Monitoring and logs
Metrics dashboard - Visualize performance metrics for your databases.

Logs explorer - Allows you to view detailed logs to troubleshoot and analyze database activity.

Metrics scraping - You can configure instance metrics for integration with external monitoring systems.

### Educational tools
Learning resources in one place - Interactive guides, sample datasets, and directions to documentation, Developer center, and Graph Academy.

----- https://neo4j.com/docs/aura/getting-started/create-account/ -----

# Create an account

To access Neo4j Aura, you need to have an Aura account. Navigate to Neo4j Aura console and follow the instructions for registration. Once you have accepted the terms and conditions and verified your email address, you can start using the console.

The console exists in two versions,the new console, and the classic experience, as mentioned in About Neo4j Aura console. You can toggle between the different versions, via the account dropdown in the top right corner.

----- https://neo4j.com/docs/aura/getting-started/create-instance/ -----

# Create an instance

There are two types of Aura instances:

AuraDB (the default Aura instance type)

AuraDS (the fully managed version of Neo4j Graph Data Science)

Select the type of instance using the switch on the top right, then choose the plan that best suits your needs.

For AuraDB, you can upgrade your plan, and resize your instance’s memory and storage later if your needs change. For pre-paid AuraDB instances on GCP, adjustable storage independent of memory is available, see Adjust storage for more information.

You can optionally enable additional features:

Graph Analytics plugin to add graph analytics capabilities (AuraDB Professional only)

Vector optimization to enhance performance for vector-based operations

After selecting Next, your instance is created. A password is generated for the instance, ensure to either copy or download it, as it will not be recoverable after. The password is required to access your instance later.

You can only create one Free instance per account. To create more instances, you need to upgrade your plan. See Neo4j Pricing for more information on the different plans.

----- https://neo4j.com/docs/aura/getting-started/connect-instance/ -----

# Connect to an instance
To interact with a database in an instance, you need to establish a connection.

Go to Import, Explore or Query.

Select Status and from there you can connect to an instance.

You may need your Username and Password credentials.

connectionbanner1
Figure 1. Connection banner
connectionmodalnonremote
Figure 2. Connection modal
Field	Description
Connection method

The protocol is used for the communication between the Neo4j database server and the client application or tool. The default is neo4j+s//.

Single sign-on

If this is set up, you can use SSO.

Database user

Neo4j by default

Password

You are given the password when you initially create the instance

## Connection method
To connect to an instance, select one of the following connection methods: neo4j+s:// or https://

The connection method protocol is used for the communication between the Neo4j database server and the client application or tool. For more information about connection schemes, see Operations Manual → Configure network connectors and Bolt Protocol.

## neo4j+s://
Establishes a TLS-encrypted connection to Neo4j using the Bolt protocol over WebSockets, with full certificate validation. Use for optimal performance.

## https://
TLS encrypted connection to Neo4j over HTTPS (Query API), with full certificate validation. Use in environments where port restrictions may prevent access to the Bolt port.

## Errors
In an enterprise environment with restrictive networking, connection errors are sometimes caused because non-standard ports (like the Bolt protocol) are blocked by firewalls when using neo4j+s://.

Switching to https:// can address connection issues and ensure seamless connectivity without extra configuration.

----- https://neo4j.com/docs/aura/getting-started/migrate-metadata/ -----

# Migrate metadata from Workspace
If you have an Aura instance created in the classic Aura console (refer to New Neo4j Aura console for comparison), you can migrate the metadata from Workspace to the new console and continue working with your data in the new experience. The metadata includes the data model and saved Cypher queries.

## Data model
From the Import tab in Workspace, open the more menu (…​) and download the model, with or without data.

export model
Then navigate to the new console and select Import → Graph models. Once you select New graph model, you access the more menu (…​), similar to Workspace, and select Open model with or without data.

import model
Note that if you have downloaded your data with the model, you can also go a different route via Import → Data sources and select New data source and then import locally from files. This leads you to the same Import frame as the first route and you can use the more menu (…​) to open the model with your data.

## Saved Cypher
Any saved Cypher snippets can be downloaded from the Query tab in Workspace. From the Saved Cypher drawer, use the Export button to download selected queries as a .csv file.

export saved cypher
In the new console, navigate to the Query tab and open the Saved Cypher drawer. Use the Import button and select the .csv file you downloaded from Workspace.

import saved cypher

## Perspectives
Perspectives, except for the default Perspective (which is automatically re-created in the new console), can be exported from the Perspective drawer in Workspace. Use the Export option on the Perspective you want to save. It is exported as a .json file.

export perspective
In the new console, navigate to the Explore tab and open the Perspective drawer. Use the Import option and select the .json file you downloaded from Workspace.

import perspective
