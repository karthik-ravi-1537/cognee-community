import asyncio
import cognee

import os

# By default cognee uses OpenAI's gpt-5-mini LLM model
# Provide your OpenAI LLM API KEY
os.environ.setdefault("LLM_API_KEY", "")


async def cognee_demo():
    # Get file path to document to process
    from pathlib import Path

    from cognee_community_hybrid_adapter_duckdb import register

    # Please provide your Milvus instance url or local path
    cognee.config.set_vector_db_config({
        "vector_db_provider": "duckdb",
        "vector_db_url": "cognee_simple_document_demo.db",
        # "vector_db_port": 6379,
    })

    await cognee.prune.prune_data()
    print("Data pruned.")

    await cognee.prune.prune_system(metadata=True)
    print("System pruned.")

    current_directory = Path(__file__).resolve().parent
    file_path = os.path.join(current_directory, "data", "generated_story.txt")

    # Call Cognee to process document
    await cognee.add(file_path)
    await cognee.cognify()

    # Query Cognee for information from provided document
    answer = await cognee.search("List me all the important characters in The Citadel of Vorrxundra")
    print(answer)

    answer = await cognee.search("What is the main character's name?")
    print(answer)

    answer = await cognee.search("What is the main character's goal?")
    print(answer)


# Cognee is an async library, it has to be called in an async context
asyncio.run(cognee_demo())
