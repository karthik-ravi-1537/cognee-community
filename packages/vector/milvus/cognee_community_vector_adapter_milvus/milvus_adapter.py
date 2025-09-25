import asyncio
import os
from typing import TYPE_CHECKING, cast, Optional

from pymilvus import MilvusClient

if TYPE_CHECKING:
    from cognee.infrastructure.databases.vector.vector_db_interface import (
        VectorDBInterface,
    )
from cognee.infrastructure.databases.exceptions import MissingQueryParameterError
from cognee.infrastructure.databases.vector.embeddings.EmbeddingEngine import (
    EmbeddingEngine,
)
from cognee.infrastructure.databases.vector.models.ScoredResult import ScoredResult
from cognee.infrastructure.engine import DataPoint
from cognee.infrastructure.files.storage import get_file_storage
from cognee.shared.logging_utils import get_logger
from pymilvus.orm.types import DataType

logger = get_logger("MilvusAdapter")


class MilvusAdapter:
    """
    Interface for interacting with a Milvus vector database.

    This adapter conforms to the VectorDBInterface protocol by implementing
    all required methods for managing collections, creating data points,
    searching, and other vector database operations using Milvus.

    Public methods:
    - get_milvus_client
    - embed_data
    - has_collection
    - create_collection
    - create_data_points
    - create_vector_index
    - index_data_points
    - retrieve
    - search
    - batch_search
    - delete_data_points
    - prune
    """

    name = "Milvus"

    def __init__(self, url: str, api_key: str | None, embedding_engine: EmbeddingEngine):
        self.url = url
        self.api_key = api_key
        self.embedding_engine = embedding_engine
        self.VECTOR_DB_LOCK = asyncio.Lock()
        self.client = None

    def get_milvus_client(self) -> MilvusClient:
        """
        Retrieve a Milvus client instance.

        Returns a MilvusClient object configured with the provided URL and optional API key.

        Returns:
        --------
            A MilvusClient instance.
        """

        # Ensure the parent directory exists for local file-based Milvus databases
        if not self.url.startswith("http"):
            # Local file path
            db_dir = os.path.dirname(self.url)
            if db_dir:
                file_storage = get_file_storage(db_dir)
                # This is a sync operation, but we'll handle it appropriately
                try:
                    import asyncio

                    loop = asyncio.get_event_loop()
                    loop.run_until_complete(file_storage.ensure_directory_exists())
                except RuntimeError:
                    # If no event loop is running, create a temporary one
                    import asyncio

                    asyncio.run(file_storage.ensure_directory_exists())

        if not self.client:
            if self.api_key:
                self.client = MilvusClient(uri=self.url, token=self.api_key)
            else:
                self.client = MilvusClient(uri=self.url)

        return self.client

    async def embed_data(self, data: list[str]) -> list[list[float]]:
        """
        Embed text data into vectors using the embedding engine.

        Parameters:
        -----------
            data (List[str]): List of text strings to embed.

        Returns:
        --------
            List[List[float]]: List of embedding vectors.
        """
        result = await self.embedding_engine.embed_text(data)
        return cast(list[list[float]], result)

    async def has_collection(self, collection_name: str) -> bool:
        """
        Check if a collection exists in the Milvus database.

        Parameters:
        -----------
            collection_name (str): Name of the collection to check.

        Returns:
        --------
            bool: True if the collection exists, False otherwise.
        """
        client = self.get_milvus_client()
        try:
            collections = client.list_collections()
            return collection_name in collections
        except Exception as e:
            logger.error(f"Error checking collection existence: {e}")
            return False

    async def create_collection(
        self, collection_name: str, payload_schema: object | None = None
    ) -> None:
        """
        Create a new collection in the Milvus database.

        Parameters:
        -----------
            collection_name (str): Name of the collection to create.
            payload_schema: Schema for the collection (optional).

        Returns:
        --------
            None
        """
        async with self.VECTOR_DB_LOCK:
            client = self.get_milvus_client()

            # Check if collection already exists
            if await self.has_collection(collection_name):
                return

            # Define the schema for the collection
            schema = client.create_schema()
            # Determine vector dimension from embedding engine if available
            vector_dim = 1536
            if hasattr(self.embedding_engine, "get_vector_size"):
                try:
                    vector_dim = self.embedding_engine.get_vector_size()
                except Exception as e:
                    logger.error(f"Failed to get vector dimension from embedding engine: {e}")
                    raise
            # create_schema can't accept fields array due to reserved kwarg name
            schema.add_field("id", DataType.VARCHAR, is_primary=True, max_length=65535)
            schema.add_field("vector", DataType.FLOAT_VECTOR, dim=vector_dim)
            schema.add_field("text", DataType.VARCHAR, max_length=65535)
            schema.add_field("metadata", DataType.JSON)

            try:
                client.create_collection(collection_name=collection_name, schema=schema)
                logger.info(f"Created collection: {collection_name}")
            except Exception as e:
                logger.error(f"Error creating collection {collection_name}: {e}")
                raise

    async def create_data_points(self, collection_name: str, data_points: list[DataPoint]) -> None:
        """
        Create data points in the Milvus collection.

        Parameters:
        -----------
            collection_name (str): Name of the collection.
            data_points (List[DataPoint]): List of data points to create.

        Returns:
        --------
            None
        """
        if not data_points:
            return

        client = self.get_milvus_client()

        # Embed the data points
        data_vectors = await self.embed_data(
            [DataPoint.get_embeddable_data(data_point) for data_point in data_points]
        )

        try:
            for data_point, embedding in zip(data_points, data_vectors, strict=False):
                doc_data = {
                    "id": str(data_point.id),
                    "text": getattr(
                        data_point,
                        data_point.metadata.get("index_fields", ["text"])[0],
                        "",
                    ),
                    "vector": embedding,
                    "metadata": data_point.metadata,
                }


                client.insert(
                    collection_name=collection_name,
                    data=doc_data,
                )
            client.flush(collection_name)
            logger.info(
                f"Inserted {len(data_points)} data points into collection: {collection_name}"
            )
        except Exception as e:
            logger.error(f"Error inserting data points into collection {collection_name}: {e}")
            raise

    async def create_vector_index(self, collection_name: str, field_name: str = "vector") -> None:
        """
        Create a vector index on the specified field.

        Parameters:
        -----------
            collection_name (str): Name of the collection.
            field_name (str): Name of the vector field to index.

        Returns:
        --------
            None
        """
        client = self.get_milvus_client()

        collection_name = f"{collection_name}_{field_name}"

        if not await self.has_collection(collection_name):
            await self.create_collection(collection_name)

        index_params = client.prepare_index_params(
            field_name="vector",
            index_type="IVF_FLAT",
            metric_type="COSINE",
            params={"nlist": 1024},
        )

        try:
            client.create_index(
                collection_name=collection_name,
                index_params=index_params,
            )
            logger.info(
                f"Created vector index on field {field_name} in collection: {collection_name}"
            )
        except Exception as e:
            logger.error(f"Error creating vector index in collection {collection_name}: {e}")
            raise

    async def index_data_points(
        self, index_name: str, field_name: str, data_points: list[DataPoint]
    ) -> None:
        """
        Index data points in the collection.

        Parameters:
        -----------
            collection_name (str): Name of the collection.
            data_points (List[DataPoint]): List of data points to index.

        Returns:
        --------
            None
        """
        await self.create_data_points(collection_name=f"{index_name}_{field_name}", data_points=data_points)

    async def retrieve(self, collection_name: str, data_point_ids: list[str]) -> list[DataPoint]:
        """
        Retrieve data points by their IDs.

        Parameters:
        -----------
            collection_name (str): Name of the collection.
            data_point_ids (List[str]): List of data point IDs to retrieve.

        Returns:
        --------
            List[DataPoint]: List of retrieved data points.
        """
        client = self.get_milvus_client()

        try:
            results = client.get(
                collection_name=collection_name,
                ids=data_point_ids,
                output_fields=["id", "vector", "text", "metadata"],
            )

            data_points = []
            for result in results:
                data_point = DataPoint(
                    id=result["id"],
                    text=result["text"],
                    vector=result["vector"],
                    metadata=result["metadata"],
                )
                data_points.append(data_point)

            return data_points
        except Exception as e:
            logger.error(f"Error retrieving data points from collection {collection_name}: {e}")
            raise

    async def search(
        self,
        collection_name: str,
        query_text: str | None = None,
        query_vector: list[float] | None = None,
        limit: Optional[int] = 10,
        with_vector: bool = False,
        **kwargs: object,
    ) -> list[dict[str, object]]:
        """
        Search for similar vectors in the collection.

        Parameters:
        -----------
            collection_name (str): Name of the collection to search.
            query_text (Optional[str]): Text to search for.
            query_vector (Optional[List[float]]): Vector to search for.
            limit (int): Maximum number of results to return.
            with_vector (bool): Whether to include vectors in results.
            **kwargs: object: Additional search parameters.

        Returns:
        --------
            List[Dict[str, object]]: List of search results.
        """

        # TODO: brute_force_search passes non-existent collections like FunctionDefinition_text.
        # TODO: Redis handles similarly
        if not await self.has_collection(collection_name):
            logger.warning(f"Collection {collection_name} not found, returning empty results")
            return []

        # Determine the query vector
        if query_vector is not None:
            # Use provided vector directly
            search_vector = query_vector
        elif query_text is not None:
            # Embed the query text
            query_vectors = await self.embed_data([query_text])
            search_vector = query_vectors[0]
        else:
            raise MissingQueryParameterError()

        client = self.get_milvus_client()

        try:
            # Load the collection for search
            client.load_collection(collection_name)
            # Validate limit parameter
            if limit is None:
                stats = client.get_collection_stats(collection_name)
                limit = stats["row_count"]
            if limit == 0:
                return []

            # Perform the search
            search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}

            results = client.search(
                collection_name=collection_name,
                data=[search_vector],
                anns_field="vector",
                search_params=search_params,
                limit=limit,
                output_fields=["id", "text", "metadata"],
            )

            scored_results = []
            for result in results[0]:  # results is a list of lists
                payload = {
                    "text": result["text"],
                    "metadata": result["metadata"],
                }
                if with_vector:
                    payload["vector"] = result["vector"]

                scored_results.append(ScoredResult(
                        id=result["id"],
                        payload=payload,
                        score=result.score),
                    )

            return scored_results
        except Exception as e:
            logger.error(f"Error searching collection {collection_name}: {e}")
            raise

    async def batch_search(
        self,
        collection_name: str,
        query_texts: list[str],
        limit: Optional[int] = 10,
        with_vectors: bool = False,
        **kwargs: object,
    ) -> list[list[dict[str, object]]]:
        """
        Perform batch search for multiple query texts.

        Parameters:
        -----------
            collection_name (str): Name of the collection to search.
            query_texts (List[str]): List of texts to search for.
            limit (int): Maximum number of results per query.
            **kwargs: object: Additional search parameters.

        Returns:
        --------
            List[List[Dict]]: List of search results for each query.
        """
        # Embed all query texts
        query_vectors = await self.embed_data(query_texts)

        client = self.get_milvus_client()

        try:
            # Load the collection for search
            client.load_collection(collection_name)

            if limit is None:
                stats = client.get_collection_stats(collection_name)
                limit = stats["row_count"]
            if limit == 0:
                return []

            # Perform the batch search
            search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}

            results = client.search(
                collection_name=collection_name,
                data=query_vectors,
                anns_field="vector",
                search_params=search_params,
                limit=limit,
                output_fields=["id", "text", "metadata"],
            )

            batch_results = []
            for query_results in results:
                query_search_results = []
                for result in query_results:
                    payload = {
                        "text": result["text"],
                        "metadata": result["metadata"],
                    }
                    if with_vectors:
                        payload["vectors"] = result["vectors"]

                    query_search_results.append(ScoredResult(
                        id=result["id"],
                        payload=payload,
                        score=result.score),
                    )
                batch_results.append(query_search_results)

            return batch_results
        except Exception as e:
            logger.error(f"Error performing batch search in collection {collection_name}: {e}")
            raise

    async def delete_data_points(self, collection_name: str, data_point_ids: list[str]) -> None:
        """
        Delete data points from the collection.

        Parameters:
        -----------
            collection_name (str): Name of the collection.
            data_point_ids (List[str]): List of data point IDs to delete.

        Returns:
        --------
            None
        """
        client = self.get_milvus_client()

        try:
            client.delete(collection_name=collection_name, ids=data_point_ids)
            logger.info(
                f"Deleted {len(data_point_ids)} data points from collection: {collection_name}"
            )
        except Exception as e:
            logger.error(f"Error deleting data points from collection {collection_name}: {e}")
            raise

    async def prune(self) -> None:
        """
        Clean up resources and close connections.

        Returns:
        --------
            None
        """
        client = self.get_milvus_client()
        collections = client.list_collections()
        for collection_name in collections:
            client.drop_collection(collection_name)


    async def get_distance_from_collection_elements(
        self, collection_name: str, elements: list[DataPoint]
    ) -> list[float]:
        """
        Calculate distances between collection elements and given data points.

        Parameters:
        -----------
            collection_name (str): Name of the collection.
            elements (List[DataPoint]): List of data points to calculate distances for.

        Returns:
        --------
            List[float]: List of distances.
        """
        # This is a placeholder implementation
        # In a real implementation, you would calculate actual distances
        return [0.0] * len(elements)

    def get_collection_names(self):
        """
            Get names of all collections in the database.

            Returns:
                List of collection names.
        """
        client = self.get_milvus_client()
        return client.list_collections()


if TYPE_CHECKING:
    _: VectorDBInterface = MilvusAdapter("", None, None)
