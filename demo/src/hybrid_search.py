"""
Busca hibrida combinando similaridade vetorial + full-text search.
"""
from typing import Any
import numpy as np
import psycopg
from pgvector.psycopg import register_vector
from sentence_transformers import SentenceTransformer

DB_DSN = "postgresql://admin:admin123@localhost:5432/vectordb"


def hybrid_search(
    query: str, tenant_id: str, limit: int = 5
) -> list[dict[str, Any]]:
    print(f"[1/3] Gerando embedding para: '{query}'")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    query_vec = np.array(
        model.encode(query, normalize_embeddings=True), dtype=np.float32
    )

    print("[2/3] Executando busca hibrida...")
    conn = psycopg.connect(DB_DSN)
    register_vector(conn)

    with conn.cursor() as cur:
        cur.execute("SET LOCAL hnsw.ef_search = 100;")
        cur.execute("SET LOCAL hnsw.iterative_scan = 'relaxed_order';")

        cur.execute(
            """
            SELECT id, content,
                   1 - (embedding <=> %s) AS similarity
            FROM document_chunks
            WHERE tenant_id = %s
              AND embedding IS NOT NULL
            ORDER BY embedding <=> %s
            LIMIT %s
            """,
            (query_vec, tenant_id, query_vec, limit),
        )
        vector_results = cur.fetchall()

        cur.execute(
            """
            SELECT id, content,
                   ts_rank(content_tsv,
                       plainto_tsquery('portuguese', %s)) AS similarity
            FROM document_chunks
            WHERE tenant_id = %s
              AND content_tsv @@ plainto_tsquery('portuguese', %s)
            ORDER BY similarity DESC
            LIMIT %s
            """,
            (query, tenant_id, query, limit),
        )
        fts_results = cur.fetchall()

    conn.close()
    print(f"[3/3] Encontrados {len(vector_results)} vetoriais "
          f"+ {len(fts_results)} textuais\n")

    results: list[dict[str, Any]] = []
    for row in vector_results:
        results.append({
            "id": row[0],
            "content": row[1],
            "type": "vetorial",
            "score": round(row[2], 4),
        })
    for row in fts_results:
        results.append({
            "id": row[0],
            "content": row[1],
            "type": "full-text",
            "score": round(row[2], 4),
        })

    seen: set[str] = set()
    deduped = []
    for r in sorted(results, key=lambda x: x["score"], reverse=True):
        if r["content"] not in seen:
            seen.add(r["content"])
            deduped.append(r)

    return deduped[:limit]


def _list_tenants() -> str | None:
    """Lista tenants disponiveis e retorna o selecionado."""
    conn = psycopg.connect(DB_DSN)
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT tenant_id FROM document_chunks LIMIT 5")
        rows = cur.fetchall()
    conn.close()
    if not rows:
        print("Nenhum dado encontrado. Execute generate_embeddings.py primeiro.")
        return None
    print("Tenants disponiveis:")
    for i, r in enumerate(rows):
        print(f"  [{i}] {r[0]}")
    idx = int(input("Escolha: ").strip())
    return str(rows[idx][0])


if __name__ == "__main__":
    tenant_id = _list_tenants()
    if not tenant_id:
        exit(1)

    q = input("\nPergunta: ").strip()
    results = hybrid_search(q, tenant_id)
    for r in results:
        print(f"\n--- [{r['type']}] score={r['score']} ---")
        print(r["content"])
