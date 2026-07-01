-- =============================================
-- Queries de Exemplo - pgvector
-- =============================================

-- 1. KNN exato (sem indice) - busca linear
-- Lento em grandes volumes, mas recall 100%
SELECT id, content, 1 - (embedding <=> '[0.1,0.2,...]') AS similarity
FROM document_chunks
WHERE tenant_id = '...'
ORDER BY embedding <=> '[0.1,0.2,...]'
LIMIT 5;

-- 2. ANN com HNSW (indice ativado automaticamente)
-- Configura parametros de consulta
SET LOCAL hnsw.ef_search = 100;
SET LOCAL hnsw.iterative_scan = 'relaxed_order';

SELECT id, content,
       1 - (embedding <=> '[0.1,0.2,...]') AS similarity
FROM document_chunks
WHERE tenant_id = '...'
ORDER BY embedding <=> '[0.1,0.2,...]'
LIMIT 5;

-- 3. Busca hibrida: vetorial + full-text
SET LOCAL hnsw.ef_search = 100;

WITH semantic AS (
    SELECT id, content,
           1 - (embedding <=> '[0.1,0.2,...]') AS score
    FROM document_chunks
    WHERE tenant_id = '...'
    ORDER BY embedding <=> '[0.1,0.2,...]'
    LIMIT 20
),
lexical AS (
    SELECT id, content,
           ts_rank(content_tsv, plainto_tsquery('portuguese', 'busca texto')) AS score
    FROM document_chunks
    WHERE tenant_id = '...'
      AND content_tsv @@ plainto_tsquery('portuguese', 'busca texto')
    LIMIT 20
)
SELECT id, content, 'semantic' AS match_type, score
FROM semantic
UNION ALL
SELECT id, content, 'lexical' AS match_type, score
FROM lexical
ORDER BY score DESC
LIMIT 5;

-- 4. Busca exata para comparar recall vs HNSW
SELECT id, content
FROM document_chunks
WHERE tenant_id = '...'
ORDER BY embedding <=> '[0.1,0.2,...]'
LIMIT 5;
