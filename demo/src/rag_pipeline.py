"""
Pipeline RAG completo: pergunta -> embedding -> busca -> contexto -> resposta.
"""
import numpy as np
import psycopg
from pgvector.psycopg import register_vector
from sentence_transformers import SentenceTransformer

DB_DSN = "postgresql://admin:admin123@localhost:5432/vectordb"

SYSTEM_PROMPT = """Voce e um assistente de IA focado em responder duvidas sobre bancos
de dados vetoriais e pgvector. Use APENAS o contexto abaixo para responder.
Caso a resposta nao possa ser formulada a partir do contexto, informe que
nao possui dados suficientes."""


def retrieve_context(query: str, tenant_id: str, k: int = 3) -> str:
    """Busca chunks relevantes no pgvector e monta contexto."""
    model = SentenceTransformer("all-MiniLM-L6-v2")
    query_vec = np.array(
        model.encode(query, normalize_embeddings=True), dtype=np.float32
    )

    conn = psycopg.connect(DB_DSN)
    register_vector(conn)

    with conn.cursor() as cur:
        cur.execute("SET LOCAL hnsw.ef_search = 100;")
        cur.execute(
            """
            SELECT content
            FROM document_chunks
            WHERE tenant_id = %s
            ORDER BY embedding <=> %s
            LIMIT %s
            """,
            (tenant_id, query_vec, k),
        )
        rows = cur.fetchall()
    conn.close()

    blocks = [
        f"--- Fragmento {i+1} ---\n{row[0]}"
        for i, row in enumerate(rows)
    ]
    return "\n\n".join(blocks)


def generate_response(query: str, context: str) -> str:
    """Monta o prompt e retorna resposta mock.

    ponytail: resposta mock, substituir por chamada OpenAI/DeepSeek API
    quando disponivel.
    """
    ql = query.lower()
    if "hnsw" in ql:
        return (
            "O HNSW (Hierarchical Navigable Small World) e um algoritmo de "
            "busca aproximada ANN que organiza vetores em um grafo "
            "hierarquico multi-camadas. Ele permite busca eficiente em "
            "grandes volumes de dados com alta revocacao, configurado "
            "atraves dos parametros m (conexoes), ef_construction "
            "(construcao) e ef_search (busca)."
        )
    if "cosseno" in ql or "distancia" in ql:
        return (
            "A distancia de cosseno mede o angulo entre dois vetores, "
            "ignorando suas magnitudes. No pgvector, usa-se o operador <=>. "
            "E a metrica mais comum para embeddings de texto de LLMs."
        )
    return (
        "Com base nos fragmentos recuperados, nao foi possivel determinar "
        "uma resposta especifica para sua pergunta."
    )


def main() -> None:
    conn = psycopg.connect(DB_DSN)
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT tenant_id::text FROM document_chunks LIMIT 1")
        row = cur.fetchone()
        if not row:
            print("Nenhum dado encontrado. Execute generate_embeddings.py primeiro.")
            conn.close()
            return
        tenant_id = row[0]
    conn.close()

    print("=== RAG Pipeline - pgvector ===")
    print(f"Tenant: {tenant_id}\n")

    while True:
        try:
            query = input("\nPergunta (ou 'sair'): ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not query or query.lower() in ("sair", "exit", "quit"):
            break

        print("\n[1/3] Buscando contexto...")
        context = retrieve_context(query, tenant_id)

        print("[2/3] Gerando resposta...")
        answer = generate_response(query, context)

        print("[3/3] Resposta:\n")
        print(f"Contexto:\n{context}\n")
        print(f"Resposta: {answer}")


if __name__ == "__main__":
    main()
