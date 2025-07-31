import json
import os
import sys
import argparse
import cognee
import asyncio
import subprocess
from pathlib import Path
from typing import List, Dict, Any

from cognee.shared.logging_utils import get_logger, setup_logging, get_log_file_location
import importlib.util
from contextlib import redirect_stdout
import mcp.types as types
from mcp.server import FastMCP
from cognee.modules.pipelines.operations.get_pipeline_status import get_pipeline_status
from cognee.modules.data.methods.get_unique_dataset_id import get_unique_dataset_id
from cognee.modules.users.methods import get_default_user
from cognee.api.v1.cognify.code_graph_pipeline import run_code_graph_pipeline
from cognee.modules.search.types import SearchType
from cognee.shared.data_models import KnowledgeGraph
from cognee.modules.storage.utils import JSONEncoder
from cognee.tasks.storage import add_data_points


try:
    from codingagents.coding_rule_associations import (
        add_rule_associations,
        get_existing_rules,
    )
except ModuleNotFoundError:
    from .codingagents.coding_rule_associations import (
        add_rule_associations,
        get_existing_rules,
    )

from .ontology import (
    MCPServer,
    MCPTool,
    MCPToolCall,
    Developer,
    Concept,
    create_unique_id,
    SourceNodeSet,
    ProjectNodeSet,
    validate_source_nodeset,
    validate_project_nodeset,
)


mcp = FastMCP("Cognee")

logger = get_logger()

# Now register Redis adapter after logger is available
try:
    from cognee_community_vector_adapter_redis.register import RedisAdapter, use_vector_adapter
    use_vector_adapter("redis", RedisAdapter)
    logger.info("Redis vector adapter registered successfully")
except ImportError as e:
    logger.warning(f"Could not import Redis adapter: {e}")
except Exception as e:
    logger.warning(f"Could not register Redis adapter: {e}")



@mcp.tool()
async def cognee_add_developer_rules(
    base_path: str = ".", graph_model_file: str = None, graph_model_name: str = None
) -> list:
    """
    Ingest core developer rule files into Cognee's memory layer.

    This function loads a predefined set of developer-related configuration,
    rule, and documentation files from the base repository and assigns them
    to the special 'developer_rules' node set in Cognee. It ensures these
    foundational files are always part of the structured memory graph.

    Parameters
    ----------
    base_path : str
        Root path to resolve relative file paths. Defaults to current directory.

    graph_model_file : str, optional
        Optional path to a custom schema file for knowledge graph generation.

    graph_model_name : str, optional
        Optional class name to use from the graph_model_file schema.

    Returns
    -------
    list
        A message indicating how many rule files were scheduled for ingestion,
        and how to check their processing status.

    Notes
    -----
    - Each file is processed asynchronously in the background.
    - Files are attached to the 'developer_rules' node set.
    - Missing files are skipped with a logged warning.
    """

    developer_rule_paths = [
        ".cursorrules",
        ".cursor/rules",
        ".same/todos.md",
        ".windsurfrules",
        ".clinerules",
        "CLAUDE.md",
        ".sourcegraph/memory.md",
        "AGENT.md",
        "AGENTS.md",
    ]

    async def cognify_task(file_path: str) -> None:
        with redirect_stdout(sys.stderr):
            logger.info(f"Starting cognify for: {file_path}")
            try:
                await cognee.add(file_path, node_set=["developer_rules"])
                model = KnowledgeGraph
                if graph_model_file and graph_model_name:
                    model = load_class(graph_model_file, graph_model_name)
                await cognee.cognify(graph_model=model)
                logger.info(f"Cognify finished for: {file_path}")
            except Exception as e:
                logger.error(f"Cognify failed for {file_path}: {str(e)}")
                raise ValueError(f"Failed to cognify: {str(e)}")

    tasks = []
    for rel_path in developer_rule_paths:
        abs_path = os.path.join(base_path, rel_path)
        if os.path.isfile(abs_path):
            tasks.append(asyncio.create_task(cognify_task(abs_path)))
        else:
            logger.warning(f"Skipped missing developer rule file: {abs_path}")
    log_file = get_log_file_location()
    return [
        types.TextContent(
            type="text",
            text=(
                f"Started cognify for {len(tasks)} developer rule files in background.\n"
                f"All are added to the `developer_rules` node set.\n"
                f"Use `cognify_status` or check logs at {log_file} to monitor progress."
            ),
        )
    ]


@mcp.tool()
async def cognify(data: str, graph_model_file: str = None, graph_model_name: str = None) -> list:
    """
    Transform data into a structured knowledge graph in Cognee's memory layer.

    This function launches a background task that processes the provided text/file location and
    generates a knowledge graph representation. The function returns immediately while
    the processing continues in the background due to MCP timeout constraints.

    Parameters
    ----------
    data : str
        The data to be processed and transformed into structured knowledge.
        This can include natural language, file location, or any text-based information
        that should become part of the agent's memory.

    graph_model_file : str, optional
        Path to a custom schema file that defines the structure of the generated knowledge graph.
        If provided, this file will be loaded using importlib to create a custom graph model.
        Default is None, which uses Cognee's built-in KnowledgeGraph model.

    graph_model_name : str, optional
        Name of the class within the graph_model_file to instantiate as the graph model.
        Required if graph_model_file is specified.
        Default is None, which uses the default KnowledgeGraph class.

    Returns
    -------
    list
        A list containing a single TextContent object with information about the
        background task launch and how to check its status.

    Notes
    -----
    - The function launches a background task and returns immediately
    - The actual cognify process may take significant time depending on text length
    - Use the cognify_status tool to check the progress of the operation
    """

    async def cognify_task(
        data: str, graph_model_file: str = None, graph_model_name: str = None
    ) -> str:
        """Build knowledge graph from the input text"""
        # NOTE: MCP uses stdout to communicate, we must redirect all output
        #       going to stdout ( like the print function ) to stderr.
        with redirect_stdout(sys.stderr):
            logger.info("Cognify process starting.")
            if graph_model_file and graph_model_name:
                graph_model = load_class(graph_model_file, graph_model_name)
            else:
                graph_model = KnowledgeGraph

            await cognee.add(data)

            try:
                await cognee.cognify(graph_model=graph_model)
                logger.info("Cognify process finished.")
            except Exception as e:
                logger.error("Cognify process failed.")
                raise ValueError(f"Failed to cognify: {str(e)}")

    asyncio.create_task(
        cognify_task(
            data=data,
            graph_model_file=graph_model_file,
            graph_model_name=graph_model_name,
        )
    )

    log_file = get_log_file_location()
    text = (
        f"Background process launched due to MCP timeout limitations.\n"
        f"To check current cognify status use the cognify_status tool\n"
        f"or check the log file at: {log_file}"
    )

    return [
        types.TextContent(
            type="text",
            text=text,
        )
    ]


@mcp.tool(
    name="save_interaction", description="Logs user-agent interactions and query-answer pairs"
)
async def save_interaction(data: str) -> list:
    """
    Transform and save a user-agent interaction into structured knowledge.

    Parameters
    ----------
    data : str
        The input string containing user queries and corresponding agent answers.

    Returns
    -------
    list
        A list containing a single TextContent object with information about the background task launch.
    """

    async def save_user_agent_interaction(data: str) -> None:
        """Build knowledge graph from the interaction data"""
        with redirect_stdout(sys.stderr):
            logger.info("Save interaction process starting.")

            await cognee.add(data, node_set=["user_agent_interaction"])

            try:
                await cognee.cognify()
                logger.info("Save interaction process finished.")
                logger.info("Generating associated rules from interaction data.")

                await add_rule_associations(data=data, rules_nodeset_name="coding_agent_rules")

                logger.info("Associated rules generated from interaction data.")

            except Exception as e:
                logger.error("Save interaction process failed.")
                raise ValueError(f"Failed to Save interaction: {str(e)}")

    asyncio.create_task(
        save_user_agent_interaction(
            data=data,
        )
    )

    log_file = get_log_file_location()
    text = (
        f"Background process launched to process the user-agent interaction.\n"
        f"To check the current status, use the cognify_status tool or check the log file at: {log_file}"
    )

    return [
        types.TextContent(
            type="text",
            text=text,
        )
    ]


@mcp.tool()
async def codify(repo_path: str) -> list:
    """
    Analyze and generate a code-specific knowledge graph from a software repository.

    This function launches a background task that processes the provided repository
    and builds a code knowledge graph. The function returns immediately while
    the processing continues in the background due to MCP timeout constraints.

    Parameters
    ----------
    repo_path : str
        Path to the code repository to analyze. This can be a local file path or a
        relative path to a repository. The path should point to the root of the
        repository or a specific directory within it.

    Returns
    -------
    list
        A list containing a single TextContent object with information about the
        background task launch and how to check its status.

    Notes
    -----
    - The function launches a background task and returns immediately
    - The code graph generation may take significant time for larger repositories
    - Use the codify_status tool to check the progress of the operation
    - Process results are logged to the standard Cognee log file
    - All stdout is redirected to stderr to maintain MCP communication integrity
    """

    async def codify_task(repo_path: str):
        # NOTE: MCP uses stdout to communicate, we must redirect all output
        #       going to stdout ( like the print function ) to stderr.
        with redirect_stdout(sys.stderr):
            logger.info("Codify process starting.")
            results = []
            async for result in run_code_graph_pipeline(repo_path, False):
                results.append(result)
                logger.info(result)
            if all(results):
                logger.info("Codify process finished succesfully.")
            else:
                logger.info("Codify process failed.")

    asyncio.create_task(codify_task(repo_path))

    log_file = get_log_file_location()
    text = (
        f"Background process launched due to MCP timeout limitations.\n"
        f"To check current codify status use the codify_status tool\n"
        f"or you can check the log file at: {log_file}"
    )

    return [
        types.TextContent(
            type="text",
            text=text,
        )
    ]


@mcp.tool()
async def search(search_query: str, search_type: str) -> list:
    """
    Search the Cognee knowledge graph for information relevant to the query.

    This function executes a search against the Cognee knowledge graph using the
    specified query and search type. It returns formatted results based on the
    search type selected.

    Parameters
    ----------
    search_query : str
        The search query in natural language. This can be a question, instruction, or
        any text that expresses what information is needed from the knowledge graph.

    search_type : str
        The type of search to perform. Valid options include:
        - "GRAPH_COMPLETION": Returns an LLM response based on the search query and Cognee's memory
        - "RAG_COMPLETION": Returns an LLM response based on the search query and standard RAG data
        - "CODE": Returns code-related knowledge in JSON format
        - "CHUNKS": Returns raw text chunks from the knowledge graph
        - "INSIGHTS": Returns relationships between nodes in readable format

        The search_type is case-insensitive and will be converted to uppercase.

    Returns
    -------
    list
        A list containing a single TextContent object with the search results.
        The format of the result depends on the search_type:
        - For CODE: JSON-formatted search results
        - For GRAPH_COMPLETION/RAG_COMPLETION: A single text completion
        - For CHUNKS: String representation of the raw chunks
        - For INSIGHTS: Formatted string showing node relationships
        - For other types: String representation of the search results

    Notes
    -----
    - Different search types produce different output formats
    - The function handles the conversion between Cognee's internal result format and MCP's output format
    """

    async def search_task(search_query: str, search_type: str) -> str:
        """Search the knowledge graph"""
        # NOTE: MCP uses stdout to communicate, we must redirect all output
        #       going to stdout ( like the print function ) to stderr.
        with redirect_stdout(sys.stderr):
            search_results = await cognee.search(
                query_type=SearchType[search_type.upper()], query_text=search_query
            )

            if search_type.upper() == "CODE":
                return json.dumps(search_results, cls=JSONEncoder)
            elif (
                search_type.upper() == "GRAPH_COMPLETION" or search_type.upper() == "RAG_COMPLETION"
            ):
                return str(search_results[0])
            elif search_type.upper() == "CHUNKS":
                return str(search_results)
            elif search_type.upper() == "INSIGHTS":
                results = retrieved_edges_to_string(search_results)
                return results
            else:
                return str(search_results)

    search_results = await search_task(search_query, search_type)
    return [types.TextContent(type="text", text=search_results)]


@mcp.tool()
async def get_developer_rules() -> list:
    """
    Retrieve all developer rules that were generated based on previous interactions.

    This tool queries the Cognee knowledge graph and returns a list of developer
    rules.

    Parameters
    ----------
    None

    Returns
    -------
    list
        A list containing a single TextContent object with the retrieved developer rules.
        The format is plain text containing the developer rules in bulletpoints.

    Notes
    -----
    - The specific logic for fetching rules is handled internally.
    - This tool does not accept any parameters and is intended for simple rule inspection use cases.
    """

    async def fetch_rules_from_cognee() -> str:
        """Collect all developer rules from Cognee"""
        with redirect_stdout(sys.stderr):
            try:
                results = []
                
                # Get generated rules from coding_agent_rules nodeset (created by save_interaction)
                try:
                    generated_rules = await get_existing_rules(rules_nodeset_name="coding_agent_rules")
                    if generated_rules and generated_rules.strip():
                        results.append("## Generated Rules from Interactions:\n" + generated_rules)
                except Exception as e:
                    logger.warning(f"Could not fetch generated rules: {e}")
                
                # Try to get data from developer_rules nodeset using graph engine directly
                try:
                    from cognee.infrastructure.databases.graph import get_graph_engine
                    from cognee.modules.engine.models import NodeSet
                    graph_engine = await get_graph_engine()
                    
                    # Get nodes from developer_rules nodeset
                    nodes_data, _ = await graph_engine.get_nodeset_subgraph(
                        node_type=NodeSet, node_name=["developer_rules"]
                    )
                    
                    if nodes_data:
                        raw_rules_content = []
                        for item in nodes_data:
                            if isinstance(item, tuple) and len(item) == 2 and isinstance(item[1], dict):
                                # Extract relevant content from the node
                                node_content = item[1]
                                if "name" in node_content:
                                    raw_rules_content.append(f"- File: {node_content['name']}")
                                if "text" in node_content:
                                    raw_rules_content.append(f"  Content: {node_content['text'][:200]}...")
                        
                        if raw_rules_content:
                            results.append("\n## Developer Rule Files:\n" + "\n".join(raw_rules_content))
                except Exception as e:
                    logger.warning(f"Could not fetch raw rule files: {e}")
                
                if not results:
                    return "No developer rules found. Use add_developer_rules to ingest rule files or save_interaction to generate rules from conversations."
                
                return "\n".join(results)
                
            except Exception as e:
                logger.error(f"Error fetching developer rules: {e}")
                return f"Error retrieving developer rules: {str(e)}"

    rules_text = await fetch_rules_from_cognee()

    return [types.TextContent(type="text", text=rules_text)]


@mcp.tool()
async def list_data(dataset_id: str = None) -> list:
    """
    List all datasets and their data items with IDs for deletion operations.

    This function helps users identify data IDs and dataset IDs that can be used
    with the delete tool. It provides a comprehensive view of available data.

    Parameters
    ----------
    dataset_id : str, optional
        If provided, only list data items from this specific dataset.
        If None, lists all datasets and their data items.
        Should be a valid UUID string.

    Returns
    -------
    list
        A list containing a single TextContent object with formatted information
        about datasets and data items, including their IDs for deletion.

    Notes
    -----
    - Use this tool to identify data_id and dataset_id values for the delete tool
    - The output includes both dataset information and individual data items
    - UUIDs are displayed in a format ready for use with other tools
    """
    from uuid import UUID

    with redirect_stdout(sys.stderr):
        try:
            user = await get_default_user()
            output_lines = []

            if dataset_id:
                # List data for specific dataset
                logger.info(f"Listing data for dataset: {dataset_id}")
                dataset_uuid = UUID(dataset_id)

                # Get the dataset information
                from cognee.modules.data.methods import get_dataset, get_dataset_data

                dataset = await get_dataset(user.id, dataset_uuid)

                if not dataset:
                    return [
                        types.TextContent(type="text", text=f"❌ Dataset not found: {dataset_id}")
                    ]

                # Get data items in the dataset
                data_items = await get_dataset_data(dataset.id)

                output_lines.append(f"📁 Dataset: {dataset.name}")
                output_lines.append(f"   ID: {dataset.id}")
                output_lines.append(f"   Created: {dataset.created_at}")
                output_lines.append(f"   Data items: {len(data_items)}")
                output_lines.append("")

                if data_items:
                    for i, data_item in enumerate(data_items, 1):
                        output_lines.append(f"   📄 Data item #{i}:")
                        output_lines.append(f"      Data ID: {data_item.id}")
                        output_lines.append(f"      Name: {data_item.name or 'Unnamed'}")
                        output_lines.append(f"      Created: {data_item.created_at}")
                        output_lines.append("")
                else:
                    output_lines.append("   (No data items in this dataset)")

            else:
                # List all datasets
                logger.info("Listing all datasets")
                from cognee.modules.data.methods import get_datasets

                datasets = await get_datasets(user.id)

                if not datasets:
                    return [
                        types.TextContent(
                            type="text",
                            text="📂 No datasets found.\nUse the cognify tool to create your first dataset!",
                        )
                    ]

                output_lines.append("📂 Available Datasets:")
                output_lines.append("=" * 50)
                output_lines.append("")

                for i, dataset in enumerate(datasets, 1):
                    # Get data count for each dataset
                    from cognee.modules.data.methods import get_dataset_data

                    data_items = await get_dataset_data(dataset.id)

                    output_lines.append(f"{i}. 📁 {dataset.name}")
                    output_lines.append(f"   Dataset ID: {dataset.id}")
                    output_lines.append(f"   Created: {dataset.created_at}")
                    output_lines.append(f"   Data items: {len(data_items)}")
                    output_lines.append("")

                output_lines.append("💡 To see data items in a specific dataset, use:")
                output_lines.append('   list_data(dataset_id="your-dataset-id-here")')
                output_lines.append("")
                output_lines.append("🗑️  To delete specific data, use:")
                output_lines.append('   delete(data_id="data-id", dataset_id="dataset-id")')

            result_text = "\n".join(output_lines)
            logger.info("List data operation completed successfully")

            return [types.TextContent(type="text", text=result_text)]

        except ValueError as e:
            error_msg = f"❌ Invalid UUID format: {str(e)}"
            logger.error(error_msg)
            return [types.TextContent(type="text", text=error_msg)]

        except Exception as e:
            error_msg = f"❌ Failed to list data: {str(e)}"
            logger.error(f"List data error: {str(e)}")
            return [types.TextContent(type="text", text=error_msg)]


@mcp.tool()
async def delete(data_id: str, dataset_id: str, mode: str = "soft") -> list:
    """
    Delete specific data from a dataset in the Cognee knowledge graph.

    This function removes a specific data item from a dataset while keeping the
    dataset itself intact. It supports both soft and hard deletion modes.

    Parameters
    ----------
    data_id : str
        The UUID of the data item to delete from the knowledge graph.
        This should be a valid UUID string identifying the specific data item.

    dataset_id : str
        The UUID of the dataset containing the data to be deleted.
        This should be a valid UUID string identifying the dataset.

    mode : str, optional
        The deletion mode to use. Options are:
        - "soft" (default): Removes the data but keeps related entities that might be shared
        - "hard": Also removes degree-one entity nodes that become orphaned after deletion
        Default is "soft" for safer deletion that preserves shared knowledge.

    Returns
    -------
    list
        A list containing a single TextContent object with the deletion results,
        including status, deleted node counts, and confirmation details.

    Notes
    -----
    - This operation cannot be undone. The specified data will be permanently removed.
    - Hard mode may remove additional entity nodes that become orphaned
    - The function provides detailed feedback about what was deleted
    - Use this for targeted deletion instead of the prune tool which removes everything
    """
    from uuid import UUID

    with redirect_stdout(sys.stderr):
        try:
            logger.info(
                f"Starting delete operation for data_id: {data_id}, dataset_id: {dataset_id}, mode: {mode}"
            )

            # Convert string UUIDs to UUID objects
            data_uuid = UUID(data_id)
            dataset_uuid = UUID(dataset_id)

            # Get default user for the operation
            user = await get_default_user()

            # Call the cognee delete function
            result = await cognee.delete(
                data_id=data_uuid, dataset_id=dataset_uuid, mode=mode, user=user
            )

            logger.info(f"Delete operation completed successfully: {result}")

            # Format the result for MCP response
            formatted_result = json.dumps(result, indent=2, cls=JSONEncoder)

            return [
                types.TextContent(
                    type="text",
                    text=f"✅ Delete operation completed successfully!\n\n{formatted_result}",
                )
            ]

        except ValueError as e:
            # Handle UUID parsing errors
            error_msg = f"❌ Invalid UUID format: {str(e)}"
            logger.error(error_msg)
            return [types.TextContent(type="text", text=error_msg)]

        except Exception as e:
            # Handle all other errors (DocumentNotFoundError, DatasetNotFoundError, etc.)
            error_msg = f"❌ Delete operation failed: {str(e)}"
            logger.error(f"Delete operation error: {str(e)}")
            return [types.TextContent(type="text", text=error_msg)]


@mcp.tool()
async def prune():
    """
    Reset the Cognee knowledge graph by removing all stored information.

    This function performs a complete reset of both the data layer and system layer
    of the Cognee knowledge graph, removing all nodes, edges, and associated metadata.
    It is typically used during development or when needing to start fresh with a new
    knowledge base.

    Returns
    -------
    list
        A list containing a single TextContent object with confirmation of the prune operation.

    Notes
    -----
    - This operation cannot be undone. All memory data will be permanently deleted.
    - The function prunes both data content (using prune_data) and system metadata (using prune_system)
    """
    with redirect_stdout(sys.stderr):
        await cognee.prune.prune_data()
        await cognee.prune.prune_system(metadata=True)
        return [types.TextContent(type="text", text="Pruned")]


@mcp.tool()
async def cognify_status():
    """
    Get the current status of the cognify pipeline.

    This function retrieves information about current and recently completed cognify operations
    in the main_dataset. It provides details on progress, success/failure status, and statistics
    about the processed data.

    Returns
    -------
    list
        A list containing a single TextContent object with the status information as a string.
        The status includes information about active and completed jobs for the cognify_pipeline.

    Notes
    -----
    - The function retrieves pipeline status specifically for the "cognify_pipeline" on the "main_dataset"
    - Status information includes job progress, execution time, and completion status
    - The status is returned in string format for easy reading
    """
    with redirect_stdout(sys.stderr):
        user = await get_default_user()
        status = await get_pipeline_status(
            [await get_unique_dataset_id("main_dataset", user)], "cognify_pipeline"
        )
        return [types.TextContent(type="text", text=str(status))]


@mcp.tool()
async def codify_status():
    """
    Get the current status of the codify pipeline.

    This function retrieves information about current and recently completed codify operations
    in the codebase dataset. It provides details on progress, success/failure status, and statistics
    about the processed code repositories.

    Returns
    -------
    list
        A list containing a single TextContent object with the status information as a string.
        The status includes information about active and completed jobs for the cognify_code_pipeline.

    Notes
    -----
    - The function retrieves pipeline status specifically for the "cognify_code_pipeline" on the "codebase" dataset
    - Status information includes job progress, execution time, and completion status
    - The status is returned in string format for easy reading
    """
    with redirect_stdout(sys.stderr):
        user = await get_default_user()
        status = await get_pipeline_status(
            [await get_unique_dataset_id("codebase", user)], "cognify_code_pipeline"
        )
        return [types.TextContent(type="text", text=str(status))]


def node_to_string(node):
    node_data = ", ".join(
        [f'{key}: "{value}"' for key, value in node.items() if key in ["id", "name"]]
    )

    return f"Node({node_data})"


def retrieved_edges_to_string(search_results):
    edge_strings = []
    for triplet in search_results:
        node1, edge, node2 = triplet
        relationship_type = edge["relationship_name"]
        edge_str = f"{node_to_string(node1)} {relationship_type} {node_to_string(node2)}"
        edge_strings.append(edge_str)

    return "\n".join(edge_strings)


def load_class(model_file, model_name):
    model_file = os.path.abspath(model_file)
    spec = importlib.util.spec_from_file_location("graph_model", model_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    model_class = getattr(module, model_name)

    return model_class


@mcp.tool()
async def add_tool_call_event(
    call_id: str,
    timestamp: str,
    tool_name: str,
    tool_signature: str,
    tool_docstring: str,
    parameters: Dict[str, Any],
    result_digest: str,
    developer_id: str,
    developer_name: str,
    source_nodeset: str,
    project_nodeset: str,
    mentioned_concepts: List[Dict[str, Any]] = None,
) -> str:
    """
    Adds a complete tool call event to the knowledge graph, including the tool,
    the caller, source/project nodesets, and any mentioned concepts.
    
    Parameters
    ----------
    source_nodeset : str
        The source nodeset (e.g., "ide_cursor", "cicd_github_actions")
    project_nodeset : str
        The project nodeset (e.g., "project_cognee_mcp", "project_mycompany_backend")
    """
    # Validate nodesets
    if not validate_source_nodeset(source_nodeset):
        return f"Error: Invalid source nodeset '{source_nodeset}'. Use one of the predefined source types."
    
    if not validate_project_nodeset(project_nodeset):
        return f"Error: Invalid project nodeset '{project_nodeset}'. Must start with 'project_' and have format 'project_org_repo'."
    
    # Determine source category
    source_category = None
    if source_nodeset.startswith("ide_"):
        source_category = "ide"
    elif source_nodeset.startswith("agent_"):
        source_category = "agent"
    elif source_nodeset.startswith("cicd_"):
        source_category = "cicd"
    elif source_nodeset.startswith("build_"):
        source_category = "build"
    
    # Create source nodeset
    source_ns = SourceNodeSet(
        nodeset_id=create_unique_id(source_nodeset),
        name=source_nodeset,
        category=source_category
    )
    
    # Parse project nodeset
    project_parts = project_nodeset.split("_", 2)
    org = project_parts[1] if len(project_parts) > 1 else "unknown"
    repo = project_parts[2] if len(project_parts) > 2 else "unknown"
    
    project_ns = ProjectNodeSet(
        nodeset_id=create_unique_id(project_nodeset),
        name=project_nodeset,
        organization=org,
        repository=repo
    )
    
    developer = Developer(dev_id=developer_id, name=developer_name)
    tool = MCPTool(
        tool_id=tool_name,
        name=tool_name,
        signature=tool_signature,
        docstring=tool_docstring,
    )
    concepts = [
        Concept(
            concept_id=c.get("concept_id") or create_unique_id(c["description"]),
            description=c["description"],
        )
        for c in (mentioned_concepts or [])
        if c.get("description")
    ]
    tool_call = MCPToolCall(
        call_id=call_id,
        timestamp=timestamp,
        parameters=parameters,
        result_digest=result_digest,
        call_of=tool,
        called_by=developer,
        mentions=concepts,
        source_nodeset=source_ns,
        project_nodeset=project_ns,
    )

    await add_data_points([tool_call])
    return f"OK, I've added the tool call event '{call_id}' to the graph with source '{source_nodeset}' and project '{project_nodeset}'."


@mcp.tool()
async def get_all_tool_calls() -> List[Dict[str, Any]]:
    """
    Returns all recorded tool calls from the knowledge graph.
    """
    
    # Try using CYPHER query type with correct node filtering
    try:
        results = await cognee.search(
            query_text="MATCH (n) WHERE n.type = 'MCPToolCall' RETURN n",
            query_type=SearchType.CYPHER
        )
    except Exception as e:
        # Fallback to CHUNKS type if CYPHER fails
        try:
            results = await cognee.search(
                query_text="MCPToolCall",
                query_type=SearchType.CHUNKS
            )
        except Exception as e2:
            # Final fallback to natural language
            results = await cognee.search("Get all MCPToolCall records with their details")
    
    # Format the results to ensure consistent output
    formatted_results = []
    if isinstance(results, list):
        for result in results:
            # Extract relevant fields from each result
            if isinstance(result, dict):
                formatted_results.append(result)
            else:
                # Convert non-dict results to dict format
                formatted_results.append({"data": str(result)})
    
    return formatted_results


@mcp.tool()
async def get_tool_calls_by_developer(developer_name: str) -> List[Dict[str, Any]]:
    """
    Returns all tool calls made by a specific developer.
    """
    try:
        # Try CYPHER query with relationship traversal using correct schema
        results = await cognee.search(
            query_text=f"MATCH (d) WHERE d.type = 'Developer' AND d.name = '{developer_name}' MATCH (tc)-[]->(d) WHERE tc.type = 'MCPToolCall' RETURN tc",
            query_type=SearchType.CYPHER
        )
    except Exception:
        # Fallback to INSIGHTS type
        try:
            results = await cognee.search(
                query_text=f"MCPToolCall called by developer {developer_name}",
                query_type=SearchType.INSIGHTS
            )
        except Exception:
            # Final fallback to natural language
            results = await cognee.search(f"Find all MCPToolCall records where the developer name is {developer_name}")
    
    formatted_results = []
    if isinstance(results, list):
        for result in results:
            if isinstance(result, dict):
                formatted_results.append(result)
            else:
                formatted_results.append({"data": str(result)})
    
    return formatted_results


@mcp.tool()
async def get_tool_calls_by_tool(tool_name: str) -> List[Dict[str, Any]]:
    """
    Returns all calls for a specific tool.
    """
    try:
        # Try CYPHER query with relationship traversal using correct schema
        results = await cognee.search(
            query_text=f"MATCH (t) WHERE t.type = 'MCPTool' AND t.name = '{tool_name}' MATCH (tc)-[]->(t) WHERE tc.type = 'MCPToolCall' RETURN tc",
            query_type=SearchType.CYPHER
        )
    except Exception:
        # Fallback to INSIGHTS type
        try:
            results = await cognee.search(
                query_text=f"MCPToolCall for tool {tool_name}",
                query_type=SearchType.INSIGHTS
            )
        except Exception:
            # Final fallback to natural language
            results = await cognee.search(f"Find all MCPToolCall records for the tool named {tool_name}")
    
    formatted_results = []
    if isinstance(results, list):
        for result in results:
            if isinstance(result, dict):
                formatted_results.append(result)
            else:
                formatted_results.append({"data": str(result)})
    
    return formatted_results


@mcp.tool()
async def get_tool_calls_by_source(source_nodeset: str) -> List[Dict[str, Any]]:
    """
    Returns all tool calls from a specific source (IDE, agent, CI/CD, etc.).
    
    Parameters
    ----------
    source_nodeset : str
        The source nodeset to filter by (e.g., "ide_cursor", "cicd_github_actions")
    """
    if not validate_source_nodeset(source_nodeset):
        return [{"error": f"Invalid source nodeset '{source_nodeset}'. Use one of the predefined source types."}]
    
    try:
        # Try CYPHER query
        results = await cognee.search(
            query_text=f"MATCH (s) WHERE s.type = 'SourceNodeSet' AND s.name = '{source_nodeset}' MATCH (tc)-[]->(s) WHERE tc.type = 'MCPToolCall' RETURN tc",
            query_type=SearchType.CYPHER
        )
    except Exception:
        # Fallback to natural language
        results = await cognee.search(f"Find all MCPToolCall records from source {source_nodeset}")
    
    formatted_results = []
    if isinstance(results, list):
        for result in results:
            if isinstance(result, dict):
                formatted_results.append(result)
            else:
                formatted_results.append({"data": str(result)})
    
    return formatted_results


@mcp.tool()
async def get_tool_calls_by_project(project_nodeset: str) -> List[Dict[str, Any]]:
    """
    Returns all tool calls for a specific project/repository.
    
    Parameters
    ----------
    project_nodeset : str
        The project nodeset to filter by (e.g., "project_cognee_mcp", "project_mycompany_backend")
    """
    if not validate_project_nodeset(project_nodeset):
        return [{"error": f"Invalid project nodeset '{project_nodeset}'. Must start with 'project_' and have format 'project_org_repo'."}]
    
    try:
        # Try CYPHER query
        results = await cognee.search(
            query_text=f"MATCH (p) WHERE p.type = 'ProjectNodeSet' AND p.name = '{project_nodeset}' MATCH (tc)-[]->(p) WHERE tc.type = 'MCPToolCall' RETURN tc",
            query_type=SearchType.CYPHER
        )
    except Exception:
        # Fallback to natural language
        results = await cognee.search(f"Find all MCPToolCall records for project {project_nodeset}")
    
    formatted_results = []
    if isinstance(results, list):
        for result in results:
            if isinstance(result, dict):
                formatted_results.append(result)
            else:
                formatted_results.append({"data": str(result)})
    
    return formatted_results


@mcp.tool()
async def get_tool_calls_by_nodesets(source_nodeset: str = None, project_nodeset: str = None) -> List[Dict[str, Any]]:
    """
    Returns tool calls filtered by both source and/or project nodesets.
    
    Parameters
    ----------
    source_nodeset : str, optional
        The source nodeset to filter by (e.g., "ide_cursor", "cicd_github_actions")
    project_nodeset : str, optional
        The project nodeset to filter by (e.g., "project_cognee_mcp")
    """
    # Validate inputs
    if source_nodeset and not validate_source_nodeset(source_nodeset):
        return [{"error": f"Invalid source nodeset '{source_nodeset}'"}]
    
    if project_nodeset and not validate_project_nodeset(project_nodeset):
        return [{"error": f"Invalid project nodeset '{project_nodeset}'"}]
    
    # Build query based on provided filters
    query = "Find all MCPToolCall records"
    if source_nodeset and project_nodeset:
        query = f"Find all MCPToolCall records from source {source_nodeset} in project {project_nodeset}"
    elif source_nodeset:
        query = f"Find all MCPToolCall records from source {source_nodeset}"
    elif project_nodeset:
        query = f"Find all MCPToolCall records for project {project_nodeset}"
    
    results = await cognee.search(query)
    
    formatted_results = []
    if isinstance(results, list):
        for result in results:
            if isinstance(result, dict):
                formatted_results.append(result)
            else:
                formatted_results.append({"data": str(result)})
    
    return formatted_results


async def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--transport",
        choices=["sse", "stdio", "http"],
        default="stdio",
        help="Transport to use for communication with the client. (default: stdio)",
    )

    # HTTP transport options
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind the HTTP server to (default: 127.0.0.1)",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind the HTTP server to (default: 8000)",
    )

    parser.add_argument(
        "--path",
        default="/mcp",
        help="Path for the MCP HTTP endpoint (default: /mcp)",
    )

    parser.add_argument(
        "--log-level",
        default="info",
        choices=["debug", "info", "warning", "error"],
        help="Log level for the HTTP server (default: info)",
    )

    args = parser.parse_args()

    # Run Alembic migrations from the main cognee directory where alembic.ini is located
    print("Running database migrations...")
    migration_result = subprocess.run(
        ["python", "-m", "alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parent.parent.parent,
    )

    if migration_result.returncode != 0:
        migration_output = migration_result.stderr + migration_result.stdout
        # Check for the expected UserAlreadyExists error (which is not critical)
        if (
            "UserAlreadyExists" in migration_output
            or "User default_user@example.com already exists" in migration_output
        ):
            print("Warning: Default user already exists, continuing startup...")
        else:
            print(f"Migration failed with unexpected error: {migration_output}")
            sys.exit(1)

    print("Database migrations done.")

    logger.info(f"Starting MCP server with transport: {args.transport}")
    if args.transport == "stdio":
        await mcp.run_stdio_async()
    elif args.transport == "sse":
        logger.info(f"Running MCP server with SSE transport on {args.host}:{args.port}")
        await mcp.run_sse_async()
    elif args.transport == "http":
        logger.info(
            f"Running MCP server with Streamable HTTP transport on {args.host}:{args.port}{args.path}"
        )
        await mcp.run_streamable_http_async()


if __name__ == "__main__":
    logger = setup_logging()

    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Error initializing Cognee MCP server: {str(e)}")
        raise
