from cognee.infrastructure.databases.vector import use_vector_adapter

from .milvus_adapter import MilvusAdapter

use_vector_adapter("milvus", MilvusAdapter)
