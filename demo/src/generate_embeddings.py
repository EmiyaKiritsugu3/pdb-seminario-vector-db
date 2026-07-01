"""
Gera embeddings com sentence-transformers e insere no PostgreSQL.
"""
import uuid
import numpy as np
import psycopg
from pgvector.psycopg import register_vector
from sentence_transformers import SentenceTransformer

DB_DSN = "postgresql://admin:admin123@localhost:5432/vectordb"

CHUNKS = [
    "O pgvector e uma extensao do PostgreSQL que adiciona suporte a busca "
    "por similaridade vetorial. Permite armazenar embeddings de alta "
    "dimensionalidade gerados por modelos de IA.",
    "HNSW (Hierarchical Navigable Small World) e um algoritmo de busca "
    "aproximada ANN que organiza vetores em um grafo hierarquico "
    "multi-camadas para busca eficiente.",
    "A distancia de cosseno mede o angulo entre dois vetores, ignorando "
    "suas magnitudes. E a metrica mais usada para embeddings de texto em LLMs.",
    "A busca hibrida combina filtragem relacional tradicional com busca "
    "vetorial, permitindo consultas como 'WHERE tenant_id = X ORDER BY "
    "distancia de cosseno'.",
    "O PostgreSQL gerencia vetores grandes atraves do mecanismo TOAST, que "
    "armazena atributos que excedem 2KB em tabelas secundarias.",
    "O parametro ef_construction controla a qualidade do grafo HNSW durante "
    "sua construcao. Valores maiores (128-256) produzem melhor recall.",
    "A Recuperacao Aumentada por Geracao (RAG) combina recuperacao de "
    "documentos com LLMs para gerar respostas fundamentadas em contexto.",
    "IVFFlat particiona o espaco vetorial em clusters de Voronoi. Cada "
    "vetor e associado ao centroide mais proximo, permitindo busca aproximada.",
    "O parametro hnsw.ef_search controla a largura da fila de prioridades "
    "durante a busca no HNSW. Valores maiores aumentam recall e latencia.",
    "O pgvector suporta tipos halfvec (float16), bit (binario) e sparsevec "
    "para dados esparsos, permitindo otimizar armazenamento por aplicacao.",
]


def generate_and_insert() -> None:
    print("[1/4] Carregando modelo all-MiniLM-L6-v2...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    print(f"[2/4] Gerando embeddings para {len(CHUNKS)} chunks...")
    embeddings = model.encode(CHUNKS, normalize_embeddings=True)
    vectors = [np.array(e, dtype=np.float32) for e in embeddings]

    print("[3/4] Conectando ao PostgreSQL...")
    conn = psycopg.connect(DB_DSN)
    register_vector(conn)

    print("[4/4] Inserindo chunks com embeddings...")
    tenant = uuid.uuid4()

    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO documents (title, author, tenant_id) "
            "VALUES (%s, %s, %s) RETURNING id",
            ("Artigo sobre pgvector", "Seminario PDB", tenant),
        )
        doc_id = cur.fetchone()[0]

        for i, (content, vec) in enumerate(zip(CHUNKS, vectors)):
            cur.execute(
                "INSERT INTO document_chunks "
                "(document_id, chunk_index, content, embedding, tenant_id) "
                "VALUES (%s, %s, %s, %s, %s)",
                (doc_id, i, content, vec, tenant),
            )

    conn.commit()
    conn.close()
    print(f"OK - {len(CHUNKS)} chunks inseridos "
          f"(doc_id={doc_id}, tenant={tenant})")


if __name__ == "__main__":
    generate_and_insert()
