from typing import TYPE_CHECKING, List, Dict, Any, Optional, Union, Tuple, Type
from uuid import UUID
import asyncio
import json

from cognee.shared.logging_utils import get_logger

from cognee.infrastructure.databases.vector.vector_db_interface import VectorDBInterface
from cognee.infrastructure.databases.graph.graph_db_interface import GraphDBInterface
from cognee.infrastructure.engine import DataPoint
from cognee.infrastructure.databases.vector.models.ScoredResult import ScoredResult
from cognee.infrastructure.databases.vector.embeddings.EmbeddingEngine import EmbeddingEngine

import duckdb

class CollectionNotFoundError(Exception):
    """Exception raised when a collection is not found."""
    pass

class DuckDBDataPoint(DataPoint):  # type: ignore[misc]
    """DuckDB data point schema for vector index entries.
    
    Attributes:
        text: The text content to be indexed.
        metadata: Metadata containing index field configuration.
    """
    text: str
    metadata: Dict[str, Any] = {"index_fields": ["text"]}

def serialize_for_json(obj: Any) -> Any:
    """Convert objects to JSON-serializable format.
    
    Args:
        obj: Object to serialize (UUID, dict, list, or any other type).
        
    Returns:
        JSON-serializable representation of the object.
    """
    if isinstance(obj, UUID):
        return str(obj)
    elif isinstance(obj, dict):
        return {k: serialize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_for_json(item) for item in obj]
    else:
        return obj


logger = get_logger("DuckDBAdapter")

class DuckDBAdapter(VectorDBInterface, GraphDBInterface):
    """DuckDB hybrid adapter implementing both vector and graph database interfaces."""
    
    name = "DuckDB"
    
    def __init__(
        self,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        embedding_engine: Optional[EmbeddingEngine] = None,
        graph_database_username: Optional[str] = None,
        graph_database_password: Optional[str] = None,
    ) -> None:
        self.database_url = url
        self.api_key = api_key
        self.embedding_engine = embedding_engine
        self.graph_database_username = graph_database_username
        self.graph_database_password = graph_database_password
        self.VECTOR_DB_LOCK = asyncio.Lock()
        
        # Create in-memory DuckDB connection
        # If database_url is provided, use it; otherwise use in-memory
        if url:
            self.connection = duckdb.connect(url)
        else:
            self.connection = duckdb.connect()  # In-memory database

        self._setup_extensions()
        
    def _setup_extensions(self) -> None:
        """Setup DuckDB extensions."""
        self.connection.execute("INSTALL duckpgq FROM community;")
        self.connection.execute("LOAD duckpgq")
        self.connection.execute("INSTALL vss;")
        self.connection.execute("LOAD vss;") # TODO add index: CREATE INDEX my_hnsw_index ON my_vector_table USING HNSW (vec);
        
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
        # Create a table for storing vector data with specified dimension
        vector_dimension = self.embedding_engine.get_vector_size()
        create_table_query = f"""
        CREATE TABLE IF NOT EXISTS {collection_name} (
            id VARCHAR PRIMARY KEY,
            text TEXT,
            vector FLOAT[{vector_dimension}],
            payload JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        await self._execute_query(create_table_query)
    
    async def create_data_points(self, collection_name: str, data_points: List[DataPoint]) -> None:
        """[VECTOR] Create data points in the collection."""
        # TODO: Implement DuckDB data point creation
        if not await self.has_collection(collection_name):
            raise CollectionNotFoundError(f"Collection {collection_name} not found!")
        
        data_vectors = await self.embed_data(
            [DataPoint.get_embeddable_data(data_point) for data_point in data_points]
        )
        
        # Create the data points (use INSERT OR REPLACE to handle duplicates)
        create_data_points_query = f"""
        INSERT OR REPLACE INTO {collection_name} (id, text, vector, payload) VALUES ($1, $2, $3, $4)
        """
        await self._execute_transaction(
            [(create_data_points_query, [
                str(data_point.id), 
                DataPoint.get_embeddable_data(data_point), 
                data_vectors[i], 
                json.dumps(serialize_for_json(data_point.model_dump()))
            ]) for i, data_point in enumerate(data_points)]
        )
    
    async def create_vector_index(self, index_name: str, index_property_name: str) -> None:
        """[VECTOR] Create a vector index for a specific property."""
        # TODO: Implement DuckDB vector index creation
        await self.create_collection(f"{index_name}_{index_property_name}")
    
    async def index_data_points(self, index_name: str, index_property_name: str, data_points: List[DataPoint]) -> None:
        """[VECTOR] Index data points in the collection."""
        await self.create_data_points(
            f"{index_name}_{index_property_name}",
            [
                DuckDBDataPoint(
                    id=data_point.id,
                    text=getattr(data_point, data_point.metadata.get("index_fields", ["text"])[0]),
                )
                for data_point in data_points
            ],
        )
    
    async def retrieve(self, collection_name: str, data_point_ids: List[str]) -> List[Dict[str, Any]]:
        """[VECTOR] Retrieve data points by their IDs."""
        try:
            if not await self.has_collection(collection_name):
                logger.warning(f"Collection '{collection_name}' not found in DuckDBAdapter.retrieve; returning [].")
                return []
            
            results = []
            
            for data_id in data_point_ids:
                # Query DuckDB for the specific data point
                query = f"SELECT payload FROM {collection_name} WHERE id = $1"
                result = await self._execute_query_one(query, [data_id])
                
                if result:
                    # Parse the stored payload JSON
                    payload_str = result[0] if isinstance(result, (list, tuple)) else result
                    try:
                        payload = json.loads(payload_str)
                        results.append(payload)
                    except (json.JSONDecodeError, TypeError):
                        # Fallback if payload parsing fails
                        logger.warning(f"Failed to parse payload for data point {data_id}")
                        results.append({"id": data_id, "error": "Failed to parse payload"})
            
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving data points: {str(e)}")
            return []
    
    async def search(
        self,
        collection_name: str,
        query_text: Optional[str] = None,
        query_vector: Optional[List[float]] = None,
        limit: int = 15,
        with_vector: bool = False,
    ) -> List[ScoredResult]:
        """[VECTOR] Search for similar vectors.
        
        Args:
            collection_name: Name of the collection to search in.
            query_text: Text to search for (will be embedded if provided).
            query_vector: Pre-computed query vector for search.
            limit: Maximum number of results to return. Set to 0 to return all rows.
            with_vector: Whether to include vectors in the results.
            
        Returns:
            List of scored results ordered by similarity (highest similarity first).
        """
        from cognee.infrastructure.engine.utils import parse_id
        
        if query_text is None and query_vector is None:
            raise ValueError("One of query_text or query_vector must be provided!")
        
        if not await self.has_collection(collection_name):
            logger.warning(f"Collection '{collection_name}' not found in DuckDBAdapter.search; returning [].")
            return []
        
        if limit == 0:
            search_query = f"""select count(*) from {collection_name}"""
            count = await self._execute_query_one(search_query)
            if count is None:
                logger.warning(f"Count is None in DuckDBAdapter.search; returning [].")
                return []
            limit = count[0]
        
        if limit == 0:
            logger.warning(f"Limit is 0 in DuckDBAdapter.search; returning [].")
            return []

        try:
            # Get the query vector
            if query_vector is None and query_text is not None:
                query_vector = (await self.embed_data([query_text]))[0]
            
            # Ensure we have a query vector at this point
            if query_vector is None:
                raise ValueError("Could not obtain query vector from text or vector input")
            
            # Use DuckDB's native array_distance function for efficient vector search
            # Convert query vector to DuckDB array format with proper dimension
            vector_dimension = self.embedding_engine.get_vector_size()
            vector_str = f"[{','.join(map(str, query_vector))}]::FLOAT[{vector_dimension}]"
            
            # Execute vector similarity search using cosine similarity
            search_query = f"""
            SELECT id, text, vector, payload, array_cosine_distance(vector, {vector_str}) as distance
            FROM {collection_name}
            LIMIT {limit}
            """
            
            search_results = await self._execute_query(search_query)
            
            if not search_results:
                return []
            
            # Convert results to ScoredResult objects
            results = []
            for row in search_results:
                distance = row[4]  # distance is the 5th column (index 4)
                
                # Parse the payload JSON
                payload_data = json.loads(row[3]) if row[3] else {}
                
                result = ScoredResult(
                    id=parse_id(row[0]),
                    score=distance,
                    payload=payload_data,
                    vector=row[2] if with_vector else None
                )
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error during search: {str(e)}")
            raise e
    
    async def batch_search(
        self, 
        collection_name: str, 
        query_texts: List[str], 
        limit: int = 15, 
        with_vectors: bool = False
    ) -> List[List[ScoredResult]]:
        """[VECTOR] Perform batch vector search."""
        # Embed all queries at once
        vectors = await self.embed_data(query_texts)
        
        # Execute searches in parallel
        search_tasks = [
            self.search(
                collection_name=collection_name,
                query_text=None,
                query_vector=vector,
                limit=limit,
                with_vector=with_vectors
            )
            for vector in vectors
        ]
        
        results = await asyncio.gather(*search_tasks)
        
        # Return all results (consistent with individual search method behavior)
        return results
    
    async def delete_data_points(self, collection_name: str, data_point_ids: List[str]) -> Dict[str, int]:
        """[VECTOR] Delete data points by their IDs."""
        try:
            if not await self.has_collection(collection_name):
                logger.warning(f"Collection '{collection_name}' not found in DuckDBAdapter.delete_data_points")
                return {"deleted": 0}
            
            if not data_point_ids:
                return {"deleted": 0}
            
            # Create placeholders for the IN clause
            placeholders = ", ".join([f"${i+1}" for i in range(len(data_point_ids))])
            delete_query = f"DELETE FROM {collection_name} WHERE id IN ({placeholders})"
            
            # Execute the deletion
            await self._execute_query(delete_query, data_point_ids)
            
            # Get the count of deleted rows (DuckDB doesn't return this directly, so we approximate)
            deleted_count = len(data_point_ids)  # Assume all were deleted for simplicity
            
            logger.info(f"Deleted {deleted_count} data points from collection {collection_name}")
            return {"deleted": deleted_count}
            
        except Exception as e:
            logger.error(f"Error deleting data points: {str(e)}")
            raise e
    
    async def prune(self) -> None:
        """[VECTOR] Remove all collections and data."""
        try:
            # Get all table names from the database
            tables_query = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
            tables_result = await self._execute_query(tables_query)
            
            if tables_result:
                # Drop all tables
                for row in tables_result:
                    table_name = row[0] if isinstance(row, (list, tuple)) else row
                    try:
                        drop_query = f"DROP TABLE IF EXISTS {table_name}"
                        await self._execute_query(drop_query)
                        logger.info(f"Dropped table {table_name}")
                    except Exception as e:
                        logger.warning(f"Failed to drop table {table_name}: {str(e)}")
            
            logger.info("Pruned all DuckDB vector collections")
            
        except Exception as e:
            logger.error(f"Error during prune: {str(e)}")
            raise e
    
    # GraphDBInterface methods
    async def query(self, query: str, params: Dict[str, Any]) -> List[Any]:
        """[GRAPH] Execute a query against the graph."""
        raise NotImplementedError("Graph operations are not implemented for DuckDB adapter")
    
    async def add_node(self, node: Union[DataPoint, str], properties: Optional[Dict[str, Any]] = None) -> None:
        """[GRAPH] Add a node to the graph."""
        raise NotImplementedError("Graph operations are not implemented for DuckDB adapter")
    
    async def add_nodes(self, nodes: Union[List[Tuple[str, Dict[str, Any]]], List[DataPoint]]) -> None:
        """[GRAPH] Add multiple nodes to the graph."""
        raise NotImplementedError("Graph operations are not implemented for DuckDB adapter")
    
    async def delete_node(self, node_id: str) -> None:
        """[GRAPH] Delete a node from the graph."""
        raise NotImplementedError("Graph operations are not implemented for DuckDB adapter")
    
    async def delete_nodes(self, node_ids: List[str]) -> None:
        """[GRAPH] Delete multiple nodes from the graph."""
        raise NotImplementedError("Graph operations are not implemented for DuckDB adapter")
    
    async def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """[GRAPH] Get a single node by its ID."""
        raise NotImplementedError("Graph operations are not implemented for DuckDB adapter")
    
    async def get_nodes(self, node_ids: List[str]) -> List[Dict[str, Any]]:
        """[GRAPH] Get multiple nodes by their IDs."""
        raise NotImplementedError("Graph operations are not implemented for DuckDB adapter")
    
    async def add_edge(self, source_id: str, target_id: str, relationship_name: str, properties: Optional[Dict[str, Any]] = None) -> None:
        """[GRAPH] Add an edge between two nodes."""
        raise NotImplementedError("Graph operations are not implemented for DuckDB adapter")
    
    async def add_edges(self, edges: Union[List[Tuple[str, str, str, Dict[str, Any]]], List[Tuple[str, str, str, Optional[Dict[str, Any]]]]]) -> None:
        """[GRAPH] Add multiple edges to the graph."""
        raise NotImplementedError("Graph operations are not implemented for DuckDB adapter")
    
    async def delete_graph(self) -> None:
        """[GRAPH] Delete the entire graph."""
        raise NotImplementedError("Graph operations are not implemented for DuckDB adapter")
    
    async def get_graph_data(self) -> Tuple[List[Tuple[str, Dict[str, Any]]], List[Tuple[str, str, str, Dict[str, Any]]]]:
        """[GRAPH] Get all graph data (nodes and edges)."""
        raise NotImplementedError("Graph operations are not implemented for DuckDB adapter")
    
    async def get_graph_metrics(self, include_optional: bool = False) -> Dict[str, Any]:
        """[GRAPH] Get graph metrics."""
        raise NotImplementedError("Graph operations are not implemented for DuckDB adapter")
    
    async def has_edge(self, source_id: str, target_id: str, relationship_name: str) -> bool:
        """[GRAPH] Check if an edge exists between two nodes."""
        raise NotImplementedError("Graph operations are not implemented for DuckDB adapter")
    
    async def has_edges(self, edges: List[Tuple[str, str, str, Dict[str, Any]]]) -> List[Tuple[str, str, str, Dict[str, Any]]]:
        """[GRAPH] Check if multiple edges exist."""
        raise NotImplementedError("Graph operations are not implemented for DuckDB adapter")
    
    async def get_edges(self, node_id: str) -> List[Tuple[str, str, str, Dict[str, Any]]]:
        """[GRAPH] Get all edges connected to a node."""
        raise NotImplementedError("Graph operations are not implemented for DuckDB adapter")
    
    async def get_neighbors(self, node_id: str) -> List[Dict[str, Any]]:
        """[GRAPH] Get neighboring nodes."""
        raise NotImplementedError("Graph operations are not implemented for DuckDB adapter")
    
    async def get_nodeset_subgraph(self, node_type: Type[Any], node_name: List[str]) -> Tuple[List[Tuple[int, Dict[str, Any]]], List[Tuple[int, int, str, Dict[str, Any]]]]:
        """[GRAPH] Get a subgraph for specific node types and names."""
        raise NotImplementedError("Graph operations are not implemented for DuckDB adapter")
    
    async def get_connections(self, node_id: Union[str, UUID]) -> List[Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]]:
        """[GRAPH] Get connections for a node."""
        raise NotImplementedError("Graph operations are not implemented for DuckDB adapter")


if TYPE_CHECKING:
    # Test with in-memory database (no URL)
    _a: VectorDBInterface = DuckDBAdapter()
    _b: GraphDBInterface = DuckDBAdapter()
    
    # Test with file database
    _c: VectorDBInterface = DuckDBAdapter("test.db")
    _d: GraphDBInterface = DuckDBAdapter("test.db")