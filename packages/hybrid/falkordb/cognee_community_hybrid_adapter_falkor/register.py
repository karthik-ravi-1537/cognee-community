from cognee.infrastructure.databases.graph import use_graph_adapter
from cognee.infrastructure.databases.vector import use_vector_adapter

from .falkor_adapter import FalkorDBAdapter

use_vector_adapter("falkor", FalkorDBAdapter)
use_graph_adapter("falkor", FalkorDBAdapter)
