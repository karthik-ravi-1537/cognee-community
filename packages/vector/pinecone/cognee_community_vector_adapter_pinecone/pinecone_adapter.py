import asyncio

from cognee.infrastructure.databases.exceptions import MissingQueryParameterError
from cognee.infrastructure.databases.vector import VectorDBInterface
from cognee.infrastructure.databases.vector.embeddings.EmbeddingEngine import (
    EmbeddingEngine,
)
from cognee.infrastructure.databases.vector.exceptions import CollectionNotFoundError
from cognee.infrastructure.databases.vector.models.ScoredResult import ScoredResult
from cognee.infrastructure.engine import DataPoint
from cognee.infrastructure.engine.utils import parse_id
from cognee.shared.logging_utils import get_logger
from pinecone import Pinecone, ServerlessSpec

logger = get_logger("PineconeAdapter")


class IndexSchema(DataPoint):
    text: str

    metadata: dict = {"index_fields": ["text"]}


class PineconeAdapter(VectorDBInterface):
    name = "Pinecone"
    api_key: str = None
    environment: str = None
    cloud: str = None
    region: str = None

    def __init__(self, url, api_key, embedding_engine: EmbeddingEngine, environment: str = None, cloud: str = None, region: str = None):
        self.url = url  # Not used by Pinecone, but required by Cognee interface
        self.api_key = api_key
        self.environment = environment
        self.cloud = cloud if cloud is not None else "aws"
        self.region = region if region is not None else "us-east-1"
        self.embedding_engine = embedding_engine
        self.VECTOR_DB_LOCK = asyncio.Lock()

        # Initialize Pinecone client
        self.pc = Pinecone(api_key=api_key)

    def get_pinecone_index(self, collection_name: str):
        """Get Pinecone index instance"""
        return self.pc.Index(collection_name)

    async def embed_data(self, data: list[str]) -> list[float]:
        return await self.embedding_engine.embed_text(data)

    async def has_collection(self, collection_name: str) -> bool:
        try:
            index_list = self.pc.list_indexes()
            return collection_name in [index.name for index in index_list]
        except Exception as e:
            logger.error("Error checking if collection exists: %s", str(e))
            return False

    async def create_collection(
        self,
        collection_name: str,
        payload_schema=None,
    ):
        async with self.VECTOR_DB_LOCK:
            if not await self.has_collection(collection_name):
                try:
                    self.pc.create_index(
                        name=collection_name,
                        dimension=self.embedding_engine.get_vector_size(),
                        metric="cosine",
                        spec=ServerlessSpec(
                            cloud=self.cloud,
                            region=self.region
                        )
                    )
                    logger.info("Created Pinecone index: %s", collection_name)
                except Exception as e:
                    logger.error("Error creating collection: %s", str(e))
                    raise e

    async def create_data_points(self, collection_name: str, data_points: list[DataPoint]):
        try:
            if not await self.has_collection(collection_name):
                raise CollectionNotFoundError(
                    message=f"Collection {collection_name} not found!"
                )

            index = self.get_pinecone_index(collection_name)

            data_vectors = await self.embed_data(
                [DataPoint.get_embeddable_data(data_point) for data_point in data_points]
            )

            def convert_to_pinecone_vector(data_point: DataPoint):
                # Clean metadata to only include Pinecone-compatible types
                clean_metadata = {}
                data_dump = data_point.model_dump()

                for key, value in data_dump.items():
                    if key != "metadata":  # Skip the nested metadata field that causes issues
                        if isinstance(value, (str, int, float, bool)):
                            clean_metadata[key] = value
                        elif isinstance(value, list) and all(isinstance(item, str) for item in value):
                            clean_metadata[key] = value
                        else:
                            # Convert complex types to strings
                            clean_metadata[key] = str(value)

                return {
                    "id": str(data_point.id),
                    "values": data_vectors[data_points.index(data_point)],
                    "metadata": clean_metadata
                }

            vectors = [convert_to_pinecone_vector(point) for point in data_points]

            index.upsert(vectors=vectors)
            logger.info("Uploaded %d data points to Pinecone", len(vectors))

        except Exception as error:
            logger.error("Error uploading data points to Pinecone: %s", str(error))
            raise error

    async def create_vector_index(self, index_name: str, index_property_name: str):
        await self.create_collection(f"{index_name}_{index_property_name}")

    async def index_data_points(
        self, index_name: str, index_property_name: str, data_points: list[DataPoint]
    ):
        await self.create_data_points(
            f"{index_name}_{index_property_name}",
            [
                IndexSchema(
                    id=data_point.id,
                    text=getattr(data_point, data_point.metadata["index_fields"][0]),
                )
                for data_point in data_points
            ],
        )

    async def retrieve(self, collection_name: str, data_point_ids: list[str]):
        try:
            if not await self.has_collection(collection_name):
                raise CollectionNotFoundError(
                    message=f"Collection {collection_name} not found!"
                )

            index = self.get_pinecone_index(collection_name)
            results = index.fetch(ids=data_point_ids)
            return results
        except Exception as e:
            logger.error("Error retrieving data points: %s", str(e))
            raise e

    async def search(
        self,
        collection_name: str,
        query_text: str | None = None,
        query_vector: list[float] | None = None,
        limit: int = 15,
        with_vector: bool = False,
    ) -> list[ScoredResult]:
        if query_text is None and query_vector is None:
            raise MissingQueryParameterError()

        if not await self.has_collection(collection_name):
            return []

        if query_vector is None:
            query_vector = (await self.embed_data([query_text]))[0]

        try:
            index = self.get_pinecone_index(collection_name)

            if limit == 0:
                # Pinecone doesn't have a direct count method, so we'll use a reasonable default
                # but we still need to handle the case where we want all results
                limit = 10000

            results = index.query(
                vector=query_vector,
                top_k=limit,
                include_metadata=True,
                include_values=with_vector
            )

            return [
                ScoredResult(
                    id=parse_id(match.id),
                    payload={
                        **match.metadata,
                        "id": parse_id(match.id),
                    },
                    score=match.score,  # Pinecone returns similarity score (0-1, higher = more similar)
                )
                for match in results.matches
            ]

        except Exception as e:
            logger.error("Error searching collection: %s", str(e))
            raise e

    async def batch_search(
        self,
        collection_name: str,
        query_texts: list[str],
        limit: int = None,
        with_vectors: bool = False,
    ):
        """
        Perform batch search in a Pinecone index.
        Note: Pinecone doesn't have native batch search, so we'll perform individual searches.
        """
        if limit is None:
            limit = 15

        vectors = await self.embed_data(query_texts)

        index = self.get_pinecone_index(collection_name)

        results = []
        for vector in vectors:
            try:
                result = index.query(
                    vector=vector,
                    top_k=limit,
                    include_metadata=True,
                    include_values=with_vectors
                )
                # Filter results with high similarity (>0.9)
                filtered_matches = [match for match in result.matches if match.score > 0.9]
                results.append(filtered_matches)
            except Exception as e:
                logger.error("Error in batch search: %s", str(e))
                results.append([])

        return results

    async def delete_data_points(self, collection_name: str, data_point_ids: list[str]):
        try:
            if not await self.has_collection(collection_name):
                raise CollectionNotFoundError(
                    message=f"Collection {collection_name} not found!"
                )

            index = self.get_pinecone_index(collection_name)
            results = index.delete(ids=data_point_ids)
            logger.info("Deleted %d data points from %s", len(data_point_ids), collection_name)
            return results
        except Exception as e:
            logger.error("Error deleting data points: %s", str(e))
            raise e

    async def prune(self):
        """Delete all indexes in Pinecone"""
        try:
            index_list = self.pc.list_indexes()

            for index_info in index_list:
                self.pc.delete_index(index_info.name)
                logger.info("Deleted Pinecone index: %s", index_info.name)

        except Exception as e:
            logger.error("Error pruning Pinecone indexes: %s", str(e))
            raise e
