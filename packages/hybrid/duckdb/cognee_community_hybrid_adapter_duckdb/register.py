from cognee.infrastructure.databases.vector import use_vector_adapter

from .duckdb_adapter import DuckDBAdapter

use_vector_adapter("duckdb", DuckDBAdapter)
