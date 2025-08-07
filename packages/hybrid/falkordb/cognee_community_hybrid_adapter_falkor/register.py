from cognee.infrastructure.databases import use_hybrid_adapter # TODO: sync to understand how we want to use this

from .hybrid_adapter import HybridAdapter # TODO: fill out adapter implementation

use_hybrid_adapter("falkor", HybridAdapter)