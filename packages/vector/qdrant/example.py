import asyncio
import pathlib
from os import path
import os

# NOTE: Importing the register module we let cognee know it can use the Qdrant vector adapter
from cognee_community_vector_adapter_qdrant import register


async def main():
    from cognee import config, prune, add, cognify, search, SearchType

    system_path = pathlib.Path(__file__).parent
    config.system_root_directory(path.join(system_path, ".cognee_system"))
    config.data_root_directory(path.join(system_path, ".data_storage"))

    config.set_relational_db_config(
        {
            "db_provider": "sqlite",
        }
    )
    config.set_vector_db_config(
        {
            "vector_db_provider": "qdrant",
            "vector_db_url": os.getenv("QDRANT_API_URL", "http://localhost:6333"),
            "vector_db_key": os.getenv("QDRANT_API_KEY", ""),
        }
    )
    config.set_graph_db_config(
        {
            "graph_database_provider": "kuzu",
        }
    )

    await prune.prune_data()
    await prune.prune_system(metadata=True)

    text = """
    Natural language processing (NLP) is an interdisciplinary
    subfield of computer science and information retrieval.
    """

    await add(text)

    await cognify()

    query_text = "Tell me about NLP"

    search_results = await search(
        query_type=SearchType.GRAPH_COMPLETION, query_text=query_text
    )

    for result_text in search_results:
        print(result_text)


if __name__ == "__main__":
    asyncio.run(main())
