# Cognee Community Weaviate Vector Adapter

This is a community-maintained adapter that enables Cognee to work with Weaviate as a vector database.

## Installation

```bash
pip install cognee-community-vector-adapter-weaviate
```

## Usage

```python
import asyncio
import os
from cognee import config, prune, add, cognify, search, SearchType

# Import the register module to enable Weaviate support
import cognee_community_vector_adapter_weaviate.register

async def main():
    # Configure databases
    config.set_relational_db_config({
        "db_provider": "sqlite",
    })
    config.set_vector_db_config({
        "vector_db_provider": "weaviate",
        "vector_db_url": os.getenv("VECTOR_DB_URL"),  # or your Weaviate URL
        "vector_db_key": os.getenv("VECTOR_DB_KEY"),  # or your API key
    })
    config.set_graph_db_config({
        "graph_database_provider": "networkx",
    })
    
    # Optional: Clean previous data
    await prune.prune_data()
    await prune.prune_system()
    
    # Add and process your content
    text = "Your text content here"
    await add(text)
    await cognify()
    
    # Search
    search_results = await search(
        query_type=SearchType.GRAPH_COMPLETION,
        query_text="Your search query"
    )
    
    for result in search_results:
        print(result)

if __name__ == "__main__":
    asyncio.run(main())
```

## Configuration

The Weaviate adapter requires the following configuration parameters:

- `vector_db_url`: Your Weaviate cluster endpoint URL
- `vector_db_key`: Your Weaviate API key
- `vector_db_provider`: Set to "weaviate"

### Environment Variables

Set the following environment variables or pass them directly in the config:

```bash
export VECTOR_DB_URL="https://your-weaviate-instance.weaviate.network"
export VECTOR_DB_KEY="your-api-key"
```

**Alternative:** You can also use the [`.env.template`](https://github.com/topoteretes/cognee/blob/main/.env.template) file from the main cognee repository. Copy it to your project directory, rename it to `.env`, and fill in your Weaviate configuration values.

## Requirements

- Python >= 3.11, <= 3.13
- weaviate-client >= 4.9.6, < 5.0.0
- cognee >= 0.2.1

## Features

- Full vector search capabilities
- Batch operations support
- Async/await support
- Retry logic for better reliability
- Collection management
- Data point indexing and retrieval 