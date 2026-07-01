# Design: Material do Seminário de pgvector

## Contexto

Disciplina DCT2202 - Projeto e Administração de Banco de Dados (2026.1), CERES/UFRN.
Seminário sobre Administração e Otimização de Bancos de Dados Vetoriais com PostgreSQL/pgvector.

## Entregáveis

### 1. Slides (PPTX)
13 slides cobrindo: fundamentos vetoriais, métricas de distância, pgvector, índices HNSW, busca híbrida, arquitetura RAG, benchmarks, configuração, demonstração.

### 2. Código Demo
**Infraestrutura:** Docker Compose (PostgreSQL 16 + pgvector + pg_trgm)

**SQL:**
- `01_schema.sql` — tabelas `documents` e `document_chunks` com `vector(384)`, índices HNSW (cosine), índice GIN (tsvector), B-Tree (tenant_id)
- `02_queries.sql` — KNN exato, ANN com HNSW, busca híbrida com iterative scan, full-text search

**Python:**
- `generate_embeddings.py` — sentence-transformers/all-MiniLM-L6-v2 → insere chunks no pgvector
- `hybrid_search.py` — busca combinada: filtro relacional + similaridade cosseno + full-text
- `rag_pipeline.py` — pipeline RAG completo (consulta → embedding → busca → contexto → resposta mock/LLM)

**Dados:** Chunks em português sobre pgvector, PostgreSQL, IA

### 3. PDF do Relatório
Material teórico existente + apêndices com código SQL e Python + instruções de reprodução.

### 4. Estrutura do Repositório
```
docs/
  superpowers/specs/2026-07-01-pgvector-seminario-design.md
  relatorio.pdf
demo/
  docker-compose.yml
  sql/01_schema.sql, 02_queries.sql
  src/requirements.txt, generate_embeddings.py, hybrid_search.py, rag_pipeline.py
  README.md
slides/
  slides.pptx
proposta-seminario.md
Otimização de pgvector no PostgreSQL.md
```
