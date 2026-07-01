# Demo pgvector - RAG Pipeline

## Pre-requisitos
- Docker e Docker Compose
- Python 3.10+

## Como usar

```bash
# 1. Sobe PostgreSQL com pgvector
docker compose up -d

# 2. Instala dependencias Python
pip install -r src/requirements.txt

# 3. Gera embeddings e insere dados
python src/generate_embeddings.py

# 4. Executa busca hibrida
python src/hybrid_search.py

# 5. Pipeline RAG completo
python src/rag_pipeline.py
```

## Credenciais
- Database: `vectordb`
- User: `admin`
- Password: `admin123`
- Porta: `5432`

## Estrutura
```
sql/01_schema.sql   - Tabelas + indices HNSW
sql/02_queries.sql  - Queries de exemplo
src/generate_embeddings.py - Gera embeddings e insere
src/hybrid_search.py       - Busca vetorial + full-text
src/rag_pipeline.py        - Pipeline RAG completo
```
