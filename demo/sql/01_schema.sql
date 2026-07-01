-- =============================================
-- Schema para Demo de pgvector - PDB 2026.1
-- =============================================

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Tabela de documentos mestre
CREATE TABLE documents (
    id BIGSERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    author TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    tenant_id UUID NOT NULL
);

-- Tabela de fragmentos (chunks) com embedding
CREATE TABLE document_chunks (
    id BIGSERIAL PRIMARY KEY,
    document_id BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(384),
    tenant_id UUID NOT NULL,
    metadata JSONB,
    content_tsv tsvector
        GENERATED ALWAYS AS (to_tsvector('portuguese', content)) STORED,
    UNIQUE (document_id, chunk_index)
);

-- Indices
CREATE INDEX idx_chunks_tenant ON document_chunks (tenant_id);
CREATE INDEX idx_chunks_document ON document_chunks (document_id);

CREATE INDEX idx_chunks_hnsw_cosine
    ON document_chunks USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 128);

CREATE INDEX idx_chunks_gin_lexical
    ON document_chunks USING GIN (content_tsv);
