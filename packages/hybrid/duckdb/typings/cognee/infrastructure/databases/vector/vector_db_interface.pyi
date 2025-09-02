from typing import Protocol, List, Dict, Any, Optional
from cognee.infrastructure.engine import DataPoint
from cognee.infrastructure.databases.vector.models.ScoredResult import ScoredResult

class VectorDBInterface(Protocol):
    """Protocol definition for VectorDBInterface to enable mypy checking."""

    async def embed_data(self, data: List[str]) -> List[List[float]]: ...
    async def has_collection(self, collection_name: str) -> bool: ...
    async def create_collection(self, collection_name: str) -> None: ...
    async def create_data_points(
        self, collection_name: str, data_points: List[DataPoint]
    ) -> None: ...
    async def create_vector_index(self, index_name: str, index_property_name: str) -> None: ...

    # TODO: Looks like we forgot update this method in the interface in root repo. Reflect this in the interface in root repo
    async def index_data_points(
        self, index_name: str, index_property_name: str, data_points: List[DataPoint]
    ) -> None: ...
    async def retrieve(
        self, collection_name: str, data_point_ids: List[str]
    ) -> List[Dict[str, Any]]: ...

    # TODO: Looks like we forgot update this method in the interface in root repo. Reflect this in the interface in root repo
    async def search(
        self,
        collection_name: str,
        query_text: Optional[str] = None,
        query_vector: Optional[List[float]] = None,
        limit: int = 15,
        with_vector: bool = False,
    ) -> List[ScoredResult]: ...
    async def batch_search(
        self,
        collection_name: str,
        query_texts: List[str],
        limit: int = 15,
        with_vectors: bool = False,
    ) -> List[List[ScoredResult]]: ...
    async def delete_data_points(
        self, collection_name: str, data_point_ids: List[str]
    ) -> Dict[str, int]: ...
    async def prune(self) -> None: ...
