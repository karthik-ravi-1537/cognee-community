import os
import asyncio
import pathlib
from os import path

# Please provide an API Key if needed
os.environ.setdefault("LLM_API_KEY", "")

async def main() -> None:
    from cognee import config, prune, add, cognify, search, SearchType
    # NOTE: Importing the register module we let cognee know it can use the Falkor graph adapter
    from cognee_community_hybrid_adapter_duckdb import register

    system_path = pathlib.Path(__file__).parent
    config.system_root_directory(path.join(system_path, ".cognee_system"))
    config.data_root_directory(path.join(system_path, ".data_storage"))

    # config.set_graph_db_config({
    #     "graph_database_provider": "duckdb",
    # })

    config.set_vector_db_config({
        "vector_db_provider": "duckdb",
        "vector_db_url": None,
        # "vector_db_port": 6379,
    })

    # Please provide your Falkor instance configuration
    # config.set_graph_db_config({
    #     "graph_database_url": "duckdb",
    #     "graph_database_port": 6379,
    # })
    await prune.prune_data()
    await prune.prune_system()

    await add("""
    Natural language processing (NLP) is an interdisciplinary
    subfield of computer science and information retrieval.
    """)

    await add("""
    Sandwiches are best served toasted with cheese, ham, mayo,
    lettuce, mustard, and salt & pepper.          
    """)

    await cognify()

    query_text = "Tell me about NLP"

    search_results = await search(query_type=SearchType.GRAPH_COMPLETION, query_text=query_text)

    for result_text in search_results:
        print("\nSearch result: \n" + result_text)
    
if __name__ == "__main__":
    asyncio.run(main())