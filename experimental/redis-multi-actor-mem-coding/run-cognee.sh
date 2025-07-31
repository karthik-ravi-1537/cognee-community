#!/bin/bash
source .env
export LLM_API_KEY
export GRAPH_DATABASE_PROVIDER
export VECTOR_DB_PROVIDER
export ENV=local
export TOKENIZERS_PARALLELISM=false
export EMBEDDING_PROVIDER="fastembed"
export EMBEDDING_MODEL="sentence-transformers/all-MiniLM-L6-v2"
export EMBEDDING_DIMENSIONS=384
export EMBEDDING_MAX_TOKENS=256
uv run cognee
