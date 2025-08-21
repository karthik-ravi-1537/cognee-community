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
        print(f"DuckDBAdapter: url: {url}")
        if url:
            self.connection = duckdb.connect(url)
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
            vector DOUBLE[],
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
        print(f"DuckDBAdapter: data_points: {[data_point.id for data_point in data_points]}")
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
        """[VECTOR] Search for similar vectors."""
        from cognee.exceptions import InvalidValueError
        from cognee.infrastructure.engine.utils import parse_id
        
        if query_text is None and query_vector is None:
            raise InvalidValueError("One of query_text or query_vector must be provided!")
        
        if limit <= 0:
            return []
        
        if not await self.has_collection(collection_name):
            logger.warning(f"Collection '{collection_name}' not found in DuckDBAdapter.search; returning [].")
            return []
        
        try:
            # Get the query vector
            if query_vector is None and query_text is not None:
                query_vector = (await self.embed_data([query_text]))[0]
            
            # For now, implement basic similarity search using cosine similarity
            # Note: DuckDB doesn't have built-in vector similarity functions like specialized vector DBs
            # This is a simplified implementation - in production you might want to use a proper vector extension
            
            # Get all vectors from the collection
            query = f"SELECT id, text, vector, payload FROM {collection_name}"
            all_results = await self._execute_query(query)
            
            if not all_results:
                return []
            
            # Calculate similarities (simplified cosine similarity)
            scored_results = []
            for row in all_results:
                doc_id, text, vector_str, payload_str = row
                
                try:
                    # Parse vector and payload
                    doc_vector = json.loads(vector_str) if isinstance(vector_str, str) else vector_str
                    payload = json.loads(payload_str) if isinstance(payload_str, str) else payload_str
                    
                    # Calculate cosine similarity (simplified)
                    if query_vector and doc_vector:
                        # Dot product
                        dot_product = sum(a * b for a, b in zip(query_vector, doc_vector))
                        # Magnitudes
                        mag_a = sum(a * a for a in query_vector) ** 0.5
                        mag_b = sum(b * b for b in doc_vector) ** 0.5
                        
                        # Cosine similarity (higher is better)
                        similarity = dot_product / (mag_a * mag_b) if mag_a * mag_b > 0 else 0.0
                        
                        scored_results.append(
                            ScoredResult(
                                id=parse_id(doc_id),
                                payload=payload,
                                score=similarity
                            )
                        )
                except (json.JSONDecodeError, TypeError, ValueError) as e:
                    logger.warning(f"Failed to process document {doc_id}: {e}")
                    continue
            
            # Sort by similarity (descending) and limit results
            scored_results.sort(key=lambda x: x.score, reverse=True)
            return scored_results[:limit]
            
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
        
        # Filter results by score threshold (cosine similarity, so higher is better)
        return [
            [result for result in result_group if result.score > 0.7]  # Similarity threshold
            for result_group in results
        ]
    
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
        # TODO: Implement DuckDB graph query
        return []
    
    async def add_node(self, node: Union[DataPoint, str], properties: Optional[Dict[str, Any]] = None) -> None:
        """[GRAPH] Add a node to the graph."""
        # TODO: Implement DuckDB node addition
        pass
    
    async def add_nodes(self, nodes: Union[List[Tuple[str, Dict[str, Any]]], List[DataPoint]]) -> None:
        """[GRAPH] Add multiple nodes to the graph."""
        # TODO: Implement DuckDB bulk node addition
        pass
    
    async def delete_node(self, node_id: str) -> None:
        """[GRAPH] Delete a node from the graph."""
        # TODO: Implement DuckDB node deletion
        pass
    
    async def delete_nodes(self, node_ids: List[str]) -> None:
        """[GRAPH] Delete multiple nodes from the graph."""
        # TODO: Implement DuckDB bulk node deletion
        pass
    
    async def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """[GRAPH] Get a single node by its ID."""
        # TODO: Implement DuckDB node retrieval
        return None
    
    async def get_nodes(self, node_ids: List[str]) -> List[Dict[str, Any]]:
        """[GRAPH] Get multiple nodes by their IDs."""
        # TODO: Implement DuckDB bulk node retrieval
        return []
    
    async def add_edge(self, source_id: str, target_id: str, relationship_name: str, properties: Optional[Dict[str, Any]] = None) -> None:
        """[GRAPH] Add an edge between two nodes."""
        # TODO: Implement DuckDB edge addition
        pass
    
    async def add_edges(self, edges: Union[List[Tuple[str, str, str, Dict[str, Any]]], List[Tuple[str, str, str, Optional[Dict[str, Any]]]]]) -> None:
        """[GRAPH] Add multiple edges to the graph."""
        # TODO: Implement DuckDB bulk edge addition
        pass
    
    async def delete_graph(self) -> None:
        """[GRAPH] Delete the entire graph."""
        # TODO: Implement DuckDB graph deletion
        pass
    
    async def get_graph_data(self) -> Tuple[List[Tuple[str, Dict[str, Any]]], List[Tuple[str, str, str, Dict[str, Any]]]]:
        """[GRAPH] Get all graph data (nodes and edges)."""
        # TODO: Implement DuckDB graph data retrieval
        return ([], [])
    
    async def get_graph_metrics(self, include_optional: bool = False) -> Dict[str, Any]:
        """[GRAPH] Get graph metrics."""
        # TODO: Implement DuckDB graph metrics
        return {}
    
    async def has_edge(self, source_id: str, target_id: str, relationship_name: str) -> bool:
        """[GRAPH] Check if an edge exists between two nodes."""
        # TODO: Implement DuckDB edge existence check
        return False
    
    async def has_edges(self, edges: List[Tuple[str, str, str, Dict[str, Any]]]) -> List[Tuple[str, str, str, Dict[str, Any]]]:
        """[GRAPH] Check if multiple edges exist."""
        # TODO: Implement DuckDB bulk edge existence check
        return []
    
    async def get_edges(self, node_id: str) -> List[Tuple[str, str, str, Dict[str, Any]]]:
        """[GRAPH] Get all edges connected to a node."""
        # TODO: Implement DuckDB edge retrieval
        return []
    
    async def get_neighbors(self, node_id: str) -> List[Dict[str, Any]]:
        """[GRAPH] Get neighboring nodes."""
        # TODO: Implement DuckDB neighbors retrieval
        return []
    
    async def get_nodeset_subgraph(self, node_type: Type[Any], node_name: List[str]) -> Tuple[List[Tuple[int, Dict[str, Any]]], List[Tuple[int, int, str, Dict[str, Any]]]]:
        """[GRAPH] Get a subgraph for specific node types and names."""
        # TODO: Implement DuckDB nodeset subgraph retrieval
        return ([], [])
    
    async def get_connections(self, node_id: Union[str, UUID]) -> List[Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]]:
        """[GRAPH] Get connections for a node."""
        # TODO: Implement DuckDB connections retrieval
        return []


if TYPE_CHECKING:
    # Test with in-memory database (no URL)
    _a: VectorDBInterface = DuckDBAdapter()
    _b: GraphDBInterface = DuckDBAdapter()
    
    # Test with file database
    _c: VectorDBInterface = DuckDBAdapter("test.db")
    _d: GraphDBInterface = DuckDBAdapter("test.db")