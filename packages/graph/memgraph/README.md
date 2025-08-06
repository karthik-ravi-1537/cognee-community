# Cognee Community Graph Adapter - Memgraph

This package provides a Memgraph graph database adapter for the Cognee framework.

## Installation

```bash
pip install cognee-community-graph-adapter-memgraph
```

## Usage

```python
import asyncio
import cognee
from cognee_community_graph_adapter_memgraph import register

async def main():
    # Register the Memgraph adapter
    register()
    
    # Configure cognee to use Memgraph
    cognee.config.set_graph_database_provider("memgraph")
    
    # Set up your Memgraph connection using the new config method
    cognee.config.set_graph_db_config({
        "graph_database_url": "bolt://localhost:7687",
        "graph_database_username": "memgraph",
        "graph_database_password": "memgraph"
    })
    
    # Optional: Set custom data and system directories
    cognee.config.system_root_directory("/path/to/system")
    cognee.config.data_root_directory("/path/to/data")
    
    # Add data to the knowledge graph
    sample_data = [
        "Artificial intelligence is a branch of computer science.",
        "Machine learning is a subset of AI that focuses on algorithms."
    ]
    
    await cognee.add(sample_data, "ai_knowledge")
    await cognee.cognify(["ai_knowledge"])
    
    # Search for insights and chunks
    insights = await cognee.search(
        query_type=cognee.SearchType.INSIGHTS,
        query_text="artificial intelligence"
    )
    
    chunks = await cognee.search(
        query_type=cognee.SearchType.CHUNKS,
        query_text="machine learning"
    )

if __name__ == "__main__":
    asyncio.run(main())
```

## Requirements

- Python >= 3.10, <= 3.13
- Memgraph database instance
- neo4j driver (for Bolt protocol support)

## Configuration

The adapter requires the following configuration using the `set_graph_db_config()` method:

```python
cognee.config.set_graph_db_config({
    "graph_database_url": "bolt://localhost:7687",      # Memgraph database URL
    "graph_database_username": "memgraph",              # Username for authentication
    "graph_database_password": "memgraph"               # Password for authentication
})
```

### Environment Variables

Set the following environment variables or pass them directly in the config:

```bash
export GRAPH_DATABASE_URL="bolt://localhost:7687"
export GRAPH_DATABASE_USERNAME="memgraph"
export GRAPH_DATABASE_PASSWORD="memgraph"
```

**Alternative:** You can also use the [`.env.template`](https://github.com/topoteretes/cognee/blob/main/.env.template) file from the main cognee repository. Copy it to your project directory, rename it to `.env`, and fill in your Memgraph configuration values.

### Optional Configuration

You can also set custom directories for system and data storage:

```python
cognee.config.system_root_directory("/path/to/system")
cognee.config.data_root_directory("/path/to/data")
```

## Features

- Full support for Memgraph's property graph model
- Optimized queries for graph operations
- Async/await support
- Transaction support
- Comprehensive error handling
- Search functionality for insights and chunks
- Custom directory configuration

## Example

See `example.py` for a complete working example that demonstrates:
- Setting up the Memgraph adapter
- Adding data to the knowledge graph
- Processing data with cognee
- Searching for insights and chunks
- Error handling

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License. 