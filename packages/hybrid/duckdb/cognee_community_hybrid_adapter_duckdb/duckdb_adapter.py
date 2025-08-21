from typing import TYPE_CHECKING, List, Dict, Any, Optional
from uuid import UUID
import asyncio

from cognee.infrastructure.databases.vector.vector_db_interface import VectorDBInterface
from cognee.infrastructure.databases.graph.graph_db_interface import GraphDBInterface
from cognee.infrastructure.engine import DataPoint
from cognee.infrastructure.databases.vector.models.ScoredResult import ScoredResult
from cognee.infrastructure.databases.vector.embeddings.EmbeddingEngine import EmbeddingEngine

import duckdb

class DuckDBAdapter(VectorDBInterface, GraphDBInterface):
    """DuckDB hybrid adapter implementing both vector and graph database interfaces."""
    
    name = "DuckDB"
    
    def __init__(
        self,
        database_url: Optional[str] = None,
        embedding_engine: Optional[EmbeddingEngine] = None,
        graph_database_username: Optional[str] = None,
        graph_database_password: Optional[str] = None,
    ) -> None:
        self.database_url = database_url
        self.embedding_engine = embedding_engine
        self.graph_database_username = graph_database_username
        self.graph_database_password = graph_database_password
        self.VECTOR_DB_LOCK = asyncio.Lock()
        
        # Create in-memory DuckDB connection
        # If database_url is provided, use it; otherwise use in-memory
        if database_url:
            self.connection = duckdb.connect(database_url)
        else:
            self.connection = duckdb.connect()  # In-memory database
    
    async def _execute_query(self, query: str, params: Optional[List[Any]] = None) -> Any:
        """Execute a query on the DuckDB connection with async lock."""
        async with self.VECTOR_DB_LOCK:
            if params:
                return self.connection.execute(query, params).fetchall()
            else:
                return self.connection.execute(query).fetchall()
    
    async def _execute_query_one(self, query: str, params: Optional[List[Any]] = None) -> Any:
        """Execute a query and return one result with async lock."""
        async with self.VECTOR_DB_LOCK:
            if params:
                return self.connection.execute(query, params).fetchone()
            else:
                return self.connection.execute(query).fetchone()
    
    async def _execute_transaction(self, queries: List[tuple[str, Optional[List[Any]]]]) -> None:
        """Execute multiple queries in a transaction with async lock."""
        async with self.VECTOR_DB_LOCK:
            try:
                self.connection.execute("BEGIN TRANSACTION")
                for query, params in queries:
                    if params:
                        self.connection.execute(query, params)
                    else:
                        self.connection.execute(query)
                self.connection.execute("COMMIT")
            except Exception:
                self.connection.execute("ROLLBACK")
                raise
    
    async def close(self) -> None:
        """Close the DuckDB connection safely."""
        async with self.VECTOR_DB_LOCK:
            if hasattr(self, 'connection'):
                self.connection.close()
    
    # VectorDBInterface methods
    async def embed_data(self, data: List[str]) -> List[List[float]]:
        """[VECTOR] Embed text data using the embedding engine."""
        if not self.embedding_engine:
            raise ValueError("Embedding engine not configured")
        result = await self.embedding_engine.embed_text(data)
        return result  # type: ignore[no-any-return]
    
    async def has_collection(self, collection_name: str) -> bool:
        """[VECTOR] Check if a collection exists."""
        try:
            # Check if table exists in DuckDB
            result = await self._execute_query_one(
                "SELECT table_name FROM information_schema.tables WHERE table_name = $1",
                [collection_name]
            )
            return result is not None
        except Exception:
            return False
    
    async def create_collection(self, collection_name: str) -> None:
        """[VECTOR] Create a new collection (table) in DuckDB."""
        # Example: Create a table for storing vector data
        create_table_query = f"""
        CREATE TABLE IF NOT EXISTS {collection_name} (
            id VARCHAR PRIMARY KEY,
            text TEXT,
            embedding DOUBLE[],
            metadata JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        await self._execute_query(create_table_query)
    
    async def create_data_points(self, collection_name: str, data_points: List[DataPoint]) -> None:
        """[VECTOR] Create data points in the collection."""
        # TODO: Implement DuckDB data point creation
        pass
    
    async def create_vector_index(self, index_name: str, index_property_name: str) -> None:
        """[VECTOR] Create a vector index for a specific property."""
        # TODO: Implement DuckDB vector index creation
        pass
    
    async def index_data_points(self, collection_name: str, data_points: List[DataPoint]) -> None:
        """[VECTOR] Index data points in the collection."""
        # TODO: Implement DuckDB data point indexing
        pass
    
    async def retrieve(self, collection_name: str, data_point_ids: List[str]) -> List[Dict[str, Any]]:
        """[VECTOR] Retrieve data points by their IDs."""
        # TODO: Implement DuckDB data point retrieval
        return []
    
    async def search(
        self, 
        collection_name: str, 
        query_text: str, 
        limit: int = 10,
        **kwargs: Any
    ) -> List[ScoredResult]:
        """[VECTOR] Search for similar vectors."""
        # TODO: Implement DuckDB vector search
        return []
    
    async def batch_search(
        self, 
        collection_name: str, 
        query_texts: List[str], 
        limit: int = 10,
        **kwargs: Any
    ) -> List[List[ScoredResult]]:
        """[VECTOR] Perform batch vector search."""
        # TODO: Implement DuckDB batch search
        return []
    
    async def delete_data_points(self, collection_name: str, data_point_ids: List[str]) -> Dict[str, int]:
        """[VECTOR] Delete data points by their IDs."""
        # TODO: Implement DuckDB data point deletion
        return {"deleted": 0}
    
    async def prune(self) -> None:
        """[VECTOR] Remove all collections and data."""
        # TODO: Implement DuckDB prune
        pass
    
    # GraphDBInterface methods
    async def query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """[GRAPH] Execute a query against the graph."""
        # TODO: Implement DuckDB graph query
        return []
    
    async def has_node(self, node_id: UUID) -> bool:
        """[GRAPH] Check if a node exists in the graph."""
        # TODO: Implement DuckDB node existence check
        return False
    
    async def add_node(self, node: DataPoint) -> None:
        """[GRAPH] Add a node to the graph."""
        # TODO: Implement DuckDB node addition
        pass
    
    async def add_nodes(self, nodes: List[DataPoint]) -> None:
        """[GRAPH] Add multiple nodes to the graph."""
        # TODO: Implement DuckDB bulk node addition
        pass
    
    async def extract_node(self, node_id: UUID) -> Dict[str, Any]:
        """[GRAPH] Extract a node by its ID."""
        # TODO: Implement DuckDB node extraction
        return {}
    
    async def extract_nodes(self, node_ids: List[UUID]) -> List[Dict[str, Any]]:
        """[GRAPH] Extract multiple nodes by their IDs."""
        # TODO: Implement DuckDB bulk node extraction
        return []
    
    async def delete_node(self, node_id: UUID) -> None:
        """[GRAPH] Delete a node from the graph."""
        # TODO: Implement DuckDB node deletion
        pass
    
    async def delete_nodes(self, node_ids: List[UUID]) -> None:
        """[GRAPH] Delete multiple nodes from the graph."""
        # TODO: Implement DuckDB bulk node deletion
        pass
    
    async def has_edge(self, from_node: str, to_node: str, edge_label: str) -> bool:
        """[GRAPH] Check if an edge exists between two nodes."""
        # TODO: Implement DuckDB edge existence check
        return False
    
    async def has_edges(self, edges: List[tuple[str, str, str]]) -> List[bool]:
        """[GRAPH] Check if multiple edges exist."""
        # TODO: Implement DuckDB bulk edge existence check
        return []
    
    async def add_edge(self, from_node: str, to_node: str, edge_label: str, edge_properties: Dict[str, Any]) -> None:
        """[GRAPH] Add an edge between two nodes."""
        # TODO: Implement DuckDB edge addition
        pass
    
    async def add_edges(self, edges: List[tuple[str, str, str, Dict[str, Any]]]) -> None:
        """[GRAPH] Add multiple edges to the graph."""
        # TODO: Implement DuckDB bulk edge addition
        pass
    
    async def get_edges(self, from_node: str, to_node: str) -> List[Dict[str, Any]]:
        """[GRAPH] Get edges between two nodes."""
        # TODO: Implement DuckDB edge retrieval
        return []
    
    async def get_disconnected_nodes(self) -> List[str]:
        """[GRAPH] Get nodes that have no connections."""
        # TODO: Implement DuckDB disconnected nodes retrieval
        return []
    
    async def get_predecessors(self, node_id: UUID, edge_label: Optional[str] = None) -> List[Dict[str, Any]]:
        """[GRAPH] Get predecessor nodes."""
        # TODO: Implement DuckDB predecessors retrieval
        return []
    
    async def get_successors(self, node_id: UUID, edge_label: Optional[str] = None) -> List[Dict[str, Any]]:
        """[GRAPH] Get successor nodes."""
        # TODO: Implement DuckDB successors retrieval
        return []
    
    async def get_neighbors(self, node_id: UUID) -> List[Dict[str, Any]]:
        """[GRAPH] Get neighboring nodes."""
        # TODO: Implement DuckDB neighbors retrieval
        return []
    
    async def get_connections(self, node_id: UUID) -> List[Dict[str, Any]]:
        """[GRAPH] Get connections for a node."""
        # TODO: Implement DuckDB connections retrieval
        return []
    
    async def remove_connection_to_predecessors_of(self, node_id: UUID) -> None:
        """[GRAPH] Remove connections to predecessors of a node."""
        # TODO: Implement DuckDB predecessor connection removal
        pass
    
    async def remove_connection_to_successors_of(self, node_id: UUID) -> None:
        """[GRAPH] Remove connections to successors of a node."""
        # TODO: Implement DuckDB successor connection removal
        pass
    
    async def delete_graph(self) -> None:
        """[GRAPH] Delete the entire graph."""
        # TODO: Implement DuckDB graph deletion
        pass
    
    async def get_graph_data(self) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """[GRAPH] Get all graph data (nodes and edges)."""
        # TODO: Implement DuckDB graph data retrieval
        return ([], [])
    
    async def get_graph_metrics(self) -> Dict[str, Any]:
        """[GRAPH] Get graph metrics."""
        # TODO: Implement DuckDB graph metrics
        return {}


if TYPE_CHECKING:
    # Test with in-memory database (no URL)
    _a: VectorDBInterface = DuckDBAdapter()
    _b: GraphDBInterface = DuckDBAdapter()
    
    # Test with file database
    _c: VectorDBInterface = DuckDBAdapter("test.db")
    _d: GraphDBInterface = DuckDBAdapter("test.db")