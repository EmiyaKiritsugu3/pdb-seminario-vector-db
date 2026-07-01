# Material do Seminário de pgvector — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Gerar todos os entregáveis do seminário: slides PPTX, demo prática (Docker + SQL + Python), PDF do relatório, e organizar no repositório GitHub.

**Architecture:** Repositório organizado em `slides/`, `demo/`, `docs/`. Demo usa Docker Compose (PostgreSQL 16 + pgvector), scripts SQL para schema/queries, Python para pipeline RAG com sentence-transformers.

**Tech Stack:** PostgreSQL 16, pgvector, Docker, Python, sentence-transformers, python-pptx (slides)

## Global Constraints

- Dados de exemplo em português, alinhados com conteúdo do seminário
- Embeddings usando all-MiniLM-L6-v2 (384 dims, leve, sem API key)
- Docker sem expor portas conflitantes (usar 5432 padrão)
- Código com type hints e docstrings em português
- Tabelas seguem modelo: `documents` (mestre) + `document_chunks` (chunks com embedding)

---

### Task 1: Criar estrutura de diretórios

**Files:**
- Create: `slides/.gitkeep`
- Create: `demo/sql/.gitkeep`
- Create: `demo/src/.gitkeep`
- Create: `docs/.gitkeep`

- [ ] **Step 1: Criar diretórios**

```bash
cd /home/emiyakiritsugu/Projetos_Antigravity/pdb-seminario-vector-db
mkdir -p slides demo/sql demo/src docs
touch slides/.gitkeep demo/sql/.gitkeep demo/src/.gitkeep docs/.gitkeep
```

- [ ] **Step 2: Commit**

```bash
git add slides/ demo/ docs/
git commit -m "chore: create directory structure for seminar materials"
```

---

### Task 2: Docker Compose + Config PostgreSQL

**Files:**
- Create: `demo/docker-compose.yml`

- [ ] **Step 1: Write docker-compose.yml**

```yaml
version: '3.8'
services:
  postgres:
    image: pgvector/pgvector:pg16
    container_name: pdb-pgvector
    environment:
      POSTGRES_DB: vectordb
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: admin123
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./sql:/docker-entrypoint-initdb.d
    command: >
      postgres
      -c shared_buffers=256MB
      -c effective_cache_size=768MB
      -c work_mem=64MB
      -c maintenance_work_mem=256MB
      -c max_parallel_maintenance_workers=4

volumes:
  pgdata:
```

- [ ] **Step 2: Commit**

```bash
git add demo/docker-compose.yml
git commit -m "feat: add docker-compose with pgvector tuned config"
```

---

### Task 3: SQL Schema (tabelas + índices)

**Files:**
- Create: `demo/sql/01_schema.sql`

- [ ] **Step 1: Write 01_schema.sql**

```sql
-- =============================================
-- Schema para Demo de pgvector - PDB 2026.1
-- =============================================
-- Habilita extensões
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

-- Índices
CREATE INDEX idx_chunks_tenant ON document_chunks (tenant_id);
CREATE INDEX idx_chunks_document ON document_chunks (document_id);

CREATE INDEX idx_chunks_hnsw_cosine
    ON document_chunks USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 128);

CREATE INDEX idx_chunks_gin_lexical
    ON document_chunks USING GIN (content_tsv);
```

- [ ] **Step 2: Commit**

```bash
git add demo/sql/01_schema.sql
git commit -m "feat: add SQL schema with tables, HNSW index, GIN index"
```

---

### Task 4: SQL Queries de Exemplo

**Files:**
- Create: `demo/sql/02_queries.sql`

- [ ] **Step 1: Write 02_queries.sql**

```sql
-- =============================================
-- Queries de Exemplo — pgvector
-- =============================================

-- 1. KNN exato (sem índice) - busca linear
SELECT id, content, 1 - (embedding <=> '[0.1,0.2,...]') AS similarity
FROM document_chunks
WHERE tenant_id = '...'
ORDER BY embedding <=> '[0.1,0.2,...]'
LIMIT 5;

-- 2. ANN com HNSW (índice ativado automaticamente)
SET LOCAL hnsw.ef_search = 100;
SET LOCAL hnsw.iterative_scan = 'relaxed_order';

SELECT id, content,
       1 - (embedding <=> '[0.1,0.2,...]') AS similarity
FROM document_chunks
WHERE tenant_id = '...'
ORDER BY embedding <=> '[0.1,0.2,...]'
LIMIT 5;

-- 3. Busca híbrida: vetorial + full-text
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

-- 4. Busca exata para comparar recall
SELECT id, content
FROM document_chunks
WHERE tenant_id = '...'
ORDER BY embedding <=> '[0.1,0.2,...]'
LIMIT 5;
```

- [ ] **Step 2: Commit**

```bash
git add demo/sql/02_queries.sql
git commit -m "feat: add example queries (exact, ANN, hybrid, full-text)"
```

---

### Task 5: Script Python — Conexão e Embeddings

**Files:**
- Create: `demo/src/requirements.txt`
- Create: `demo/src/generate_embeddings.py`

- [ ] **Step 1: Write requirements.txt**

```
psycopg[binary]>=3.1
sentence-transformers>=2.2
numpy>=1.24
```

- [ ] **Step 2: Write generate_embeddings.py**

```python
"""
Gera embeddings com sentence-transformers e insere no PostgreSQL.
"""
import numpy as np
import psycopg
from pgvector.psycopg import register_vector
from sentence_transformers import SentenceTransformer

DB_DSN = "postgresql://admin:admin123@localhost:5432/vectordb"

CHUNKS = [
    "O pgvector é uma extensão do PostgreSQL que adiciona suporte a busca por similaridade vetorial. Permite armazenar embeddings de alta dimensionalidade gerados por modelos de IA.",  # noqa: E501
    "HNSW (Hierarchical Navigable Small World) é um algoritmo de busca aproximada ANN que organiza vetores em um grafo hierárquico multi-camadas para busca eficiente.",  # noqa: E501
    "A distância de cosseno mede o ângulo entre dois vetores, ignorando suas magnitudes. É a métrica mais usada para embeddings de texto em LLMs.",  # noqa: E501
    "A busca híbrida combina filtragem relacional tradicional com busca vetorial, permitindo consultas como 'WHERE tenant_id = X ORDER BY distância de cosseno'.",  # noqa: E501
    "O PostgreSQL gerencia vetores grandes através do mecanismo TOAST, que armazena atributos que excedem 2KB em tabelas secundárias.",  # noqa: E501
    "O parâmetro ef_construction controla a qualidade do grafo HNSW durante sua construção. Valores maiores (128-256) produzem melhor recall.",  # noqa: E501
    "A Recuperação Aumentada por Geração (RAG) combina recuperação de documentos com LLMs para gerar respostas fundamentadas em contexto.",  # noqa: E501
    "IVFFlat particiona o espaço vetorial em clusters de Voronoi. Cada vetor é associado ao centroide mais próximo, permitindo busca aproximada.",  # noqa: E501
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
    import uuid
    tenant = uuid.uuid4()

    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO documents (title, author, tenant_id) "
            "VALUES (%s, %s, %s) RETURNING id",
            ("Artigo sobre pgvector", "Seminário PDB", tenant),
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
    print(f"OK — {len(CHUNKS)} chunks inseridos (doc_id={doc_id}, tenant={tenant})")


if __name__ == "__main__":
    generate_and_insert()
```

- [ ] **Step 3: Commit**

```bash
git add demo/src/requirements.txt demo/src/generate_embeddings.py
git commit -m "feat: add embedding generation script with model and insert"
```

---

### Task 6: Script Python — Busca Híbrida

**Files:**
- Create: `demo/src/hybrid_search.py`

- [ ] **Step 1: Write hybrid_search.py**

```python
"""
Busca híbrida combinando similaridade vetorial + full-text search.
"""
import numpy as np
import psycopg
from pgvector.psycopg import register_vector
from sentence_transformers import SentenceTransformer
from typing import Any

DB_DSN = "postgresql://admin:admin123@localhost:5432/vectordb"


def hybrid_search(query: str, tenant_id: str, limit: int = 5) -> list[dict[str, Any]]:
    print(f"[1/3] Gerando embedding para: '{query}'")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    query_vec = np.array(model.encode(query, normalize_embeddings=True), dtype=np.float32)

    print("[2/3] Executando busca híbrida...")
    conn = psycopg.connect(DB_DSN)
    register_vector(conn)

    with conn.cursor() as cur:
        # Configura parâmetros HNSW
        cur.execute("SET LOCAL hnsw.ef_search = 100;")
        cur.execute("SET LOCAL hnsw.iterative_scan = 'relaxed_order';")

        # Busca vetorial
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

        # Busca full-text
        cur.execute(
            """
            SELECT id, content,
                   ts_rank(content_tsv, plainto_tsquery('portuguese', %s)) AS similarity
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

    print(f"[3/3] Encontrados {len(vector_results)} vetoriais + {len(fts_results)} textuais\n")

    results = []
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

    # Ordena por score e deduplica
    seen = set()
    deduped = []
    for r in sorted(results, key=lambda x: x["score"], reverse=True):
        if r["content"] not in seen:
            seen.add(r["content"])
            deduped.append(r)

    return deduped[:limit]


if __name__ == "__main__":
    import uuid
    tid = input("Tenant ID (deixe vazio para listar): ").strip()
    conn = psycopg.connect(DB_DSN)
    with conn.cursor() as cur:
        if not tid:
            cur.execute("SELECT DISTINCT tenant_id FROM document_chunks LIMIT 5")
            rows = cur.fetchall()
            if not rows:
                print("Nenhum dado encontrado. Execute generate_embeddings.py primeiro.")
                conn.close()
                exit(1)
            print("Tenants disponíveis:")
            for r in rows:
                print(f"  {r[0]}")
            conn.close()
            exit(0)
    conn.close()

    query = input("\nPergunta: ").strip()
    results = hybrid_search(query, tid)
    for r in results:
        print(f"\n--- [{r['type']}] score={r['score']} ---")
        print(r["content"])
```

- [ ] **Step 2: Commit**

```bash
git add demo/src/hybrid_search.py
git commit -m "feat: add hybrid search script (vector + full-text)"
```

---

### Task 7: Script Python — Pipeline RAG

**Files:**
- Create: `demo/src/rag_pipeline.py`

- [ ] **Step 1: Write rag_pipeline.py**

```python
"""
Pipeline RAG completo: pergunta → embedding → busca → contexto → resposta.
"""
import numpy as np
import psycopg
from pgvector.psycopg import register_vector
from sentence_transformers import SentenceTransformer

DB_DSN = "postgresql://admin:admin123@localhost:5432/vectordb"

SYSTEM_PROMPT = """Você é um assistente de IA focado em responder dúvidas sobre bancos
de dados vetoriais e pgvector. Use APENAS o contexto abaixo para responder.
Caso a resposta não possa ser formulada a partir do contexto, informe que
não possui dados suficientes."""


def retrieve_context(query: str, tenant_id: str, k: int = 3) -> str:
    """Busca chunks relevantes no pgvector e monta contexto."""
    model = SentenceTransformer("all-MiniLM-L6-v2")
    query_vec = np.array(model.encode(query, normalize_embeddings=True), dtype=np.float32)

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
    """Monta o prompt e retorna resposta (mock — substituir por LLM real)."""
    # ponytail: resposta mock, substituir por chamada OpenAI/DeepSeek API
    if "hnsw" in query.lower():
        return (
            "O HNSW (Hierarchical Navigable Small World) é um algoritmo de busca "
            "aproximada ANN que organiza vetores em um grafo hierárquico "
            "multi-camadas. Ele permite busca eficiente em grandes volumes de "
            "dados com alta revocação, configurado através dos parâmetros "
            "m (conexões), ef_construction (construção) e ef_search (busca)."
        )
    if "cosseno" in query.lower() or "distância" in query.lower():
        return (
            "A distância de cosseno mede o ângulo entre dois vetores, "
            "ignorando suas magnitudes. No pgvector, usa-se o operador <=>. "
            "É a métrica mais comum para embeddings de texto de LLMs."
        )
    return (
        "Com base nos fragmentos recuperados, não foi possível determinar "
        "uma resposta específica para sua pergunta."
    )


def main() -> None:
    import uuid

    conn = psycopg.connect(DB_DSN)
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT tenant_id FROM document_chunks LIMIT 1")
        row = cur.fetchone()
        if not row:
            print("Nenhum dado encontrado. Execute generate_embeddings.py primeiro.")
            conn.close()
            return
        tenant_id = str(row[0])
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
        print(f"{SYSTEM_PROMPT}\n")
        print(f"Contexto:\n{context}\n")
        print(f"Resposta: {answer}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add demo/src/rag_pipeline.py
git commit -m "feat: add RAG pipeline script (retrieve + generate)"
```

---

### Task 8: README da Demo

**Files:**
- Create: `demo/README.md`

- [ ] **Step 1: Write README.md**

```markdown
# Demo pgvector — RAG Pipeline

## Pré-requisitos
- Docker e Docker Compose
- Python 3.10+

## Como usar

```bash
# 1. Sobe PostgreSQL com pgvector
docker compose up -d

# 2. Instala dependências Python
pip install -r src/requirements.txt

# 3. Gera embeddings e insere dados
python src/generate_embeddings.py

# 4. Executa busca híbrida
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
sql/01_schema.sql   — Tabelas + índices HNSW
sql/02_queries.sql  — Queries de exemplo
src/generate_embeddings.py — Gera embeddings e insere
src/hybrid_search.py       — Busca vetorial + full-text
src/rag_pipeline.py        — Pipeline RAG completo
```
```

- [ ] **Step 2: Commit**

```bash
git add demo/README.md
git commit -m "docs: add demo README with usage instructions"
```

---

### Task 9: Slides PPTX

**Files:**
- Create: `slides/slides.pptx`

- [ ] **Step 1: Gerar slides com python-pptx**

```bash
pip install python-pptx
```

```bash
python3 << 'PYEOF'
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)

BG = RGBColor(0x1A, 0x1A, 0x2E)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
ACCENT = RGBColor(0x00, 0xD2, 0xFF)
GRAY = RGBColor(0xAA, 0xAA, 0xAA)

def add_bg(slide):
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = BG

def add_title(slide, text, top=Inches(0.5), left=Inches(0.8), font_size=40):
    txBox = slide.shapes.add_textbox(left, top, Inches(11.5), Inches(1.2))
    tf = txBox.text_frame
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(font_size)
    p.font.color.rgb = ACCENT
    p.font.bold = True
    return tf

def add_body(slide, lines, top=Inches(2.0), left=Inches(1.0), font_size=22):
    txBox = slide.shapes.add_textbox(left, top, Inches(11.0), Inches(5.0))
    tf = txBox.text_frame
    tf.word_wrap = True
    for i, line in enumerate(lines):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        p.text = line
        p.font.size = Pt(font_size)
        p.font.color.rgb = WHITE
        p.space_after = Pt(8)
    return tf

# Slide 1: Título
slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank
add_bg(slide)
add_title(slide, "Administração e Otimização de\nBancos de Dados Vetoriais", top=Inches(1.5), font_size=44)
add_body(slide, [
    "Aplicações de Inteligência Artificial usando PostgreSQL (pgvector)",
    "",
    "DCT2202 - Projeto e Administração de Banco de Dados - T01 (2026.1)",
    "Professor: Taciano de Morais Silva",
    "Centro de Ensino Superior do Seridó - CERES/UFRN",
    "",
    "Equipe: José Inamar de Medeiros Júnior",
], top=Inches(3.5), font_size=24)

# Slide 2: Agenda
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_title(slide, "Agenda")
add_body(slide, [
    "1.  O que são Bancos Vetoriais?",
    "2.  Métricas de Distância",
    "3.  PostgreSQL + pgvector",
    "4.  Índices Vetoriais: IVFFlat vs HNSW",
    "5.  HNSW em Detalhe",
    "6.  Busca Híbrida",
    "7.  Arquitetura RAG",
    "8.  Benchmarks e Performance",
    "9.  Configuração do Ambiente",
    "10. Demonstração Prática",
    "11. Referências",
], top=Inches(1.8), font_size=24)

# Slide 3: Bancos Vetoriais
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_title(slide, "O que são Bancos Vetoriais?")
add_body(slide, [
    "Embeddings: projeção de dados não estruturados em espaços vetoriais contínuos",
    "Um embedding mapeia texto/imagem/áudio em vetor de floats (384~3072 dimensões)",
    "Proximidade geométrica ≈ similaridade semântica",
    "Principais aplicações:",
    "  → Sistemas de Recomendação",
    "  → RAG (Retrieval-Augmented Generation)",
    "  → Busca semântica",
    "  → Detecção de similaridade/anomalias",
], top=Inches(1.8), font_size=24)

# Slide 4: Métricas
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_title(slide, "Métricas de Distância")
add_body(slide, [
    "Distância Euclidiana (L2) | Operador: <-> | Distância absoluta entre pontos",
    "Produto Escalar (IP)     | Operador: <#> | Score de afinidade (MIPS)",
    "Distância de Cosseno     | Operador: <=> | Ângulo entre vetores",
    "",
    "Tabela comparativa:",
    "  Métrica          | Operador | Intervalo    | Melhor para",
    "  Euclidiana (L2)  |  <->     | [0, ∞)       | Embeddings normalizados",
    "  Produto Escalar  |  <#>     | (-∞, ∞)      | Recomendação (MIPS)",
    "  Cosseno          |  <=>     | [0, 2]       | Texto LLMs (OpenAI, Cohere)",
], top=Inches(1.8), font_size=20)

# Slide 5: PostgreSQL + pgvector
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_title(slide, "PostgreSQL + pgvector", font_size=40)
add_body(slide, [
    "Extensão nativa — sem banco vetorial separado",
    "Transações ACID unificadas: dados relacionais + vetoriais",
    "SQL padrão: integração com filtros, joins, indexes",
    "Segurança: RLS, políticas de acesso, auditoria",
    "Operadores pgvector:",
    "  <->  Distância Euclidiana L2",
    "  <#>  Produto Escalar Negativo",
    "  <=>  Distância de Cosseno",
    "Tipos: vector(n), halfvec (16-bit), bit (binário), sparsevec",
], top=Inches(1.8), font_size=24)

# Slide 6: Índices
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_title(slide, "Índices Vetoriais: IVFFlat vs HNSW")
add_body(slide, [
    "IVFFlat: Particiona espaço em clusters de Voronoi",
    "  → Busca: compara apenas clusters mais próximos (probes)",
    "  → Rápido de construir, recall inferior",
    "",
    "HNSW: Grafo hierárquico multi-camadas (inspirado em skip lists)",
    "  → Camada 0: todos os nós",
    "  → Camadas superiores: subconjuntos esparsos (dec. exponencial)",
    "  → Parâmetros: m (conexões), ef_construction, ef_search",
    "",
    "Qual escolher?",
    "  HNSW para >95% recall · IVFFlat para economia de RAM",
], top=Inches(1.8), font_size=22)

# Slide 7: HNSW
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_title(slide, "HNSW — Hierarchical Navigable Small World")
add_body(slide, [
    "Estrutura: grafo de proximidade em camadas hierárquicas",
    "Inserção: altura probabilística (dec. exponencial)",
    "Busca: greedy search do topo → base",
    "Parâmetros de criação:",
    "  m = 16 (conexões por nó, padrão)",
    "  ef_construction = 128 (qualidade da construção)",
    "Parâmetros de consulta:",
    "  ef_search = 40~200 (recall vs latência)",
    "A Maldição da Dimensionalidade:",
    "  Dimensão intrínseca (LID) afeta recall do HNSW",
    "  Ordem de inserção pode degradar recall em até 12.8pp",
], top=Inches(1.8), font_size=22)

# Slide 8: Busca Híbrida
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_title(slide, "Busca Híbrida")
add_body(slide, [
    "Unifica SQL estruturado + similaridade vetorial",
    "Estratégias:",
    "  Pre-filtering: filtro → KNN exato no subconjunto",
    "  Post-filtering: HNSW → filtro → pode perder resultados",
    "  Iterative Scan (pgvector 0.8+):",
    "    → Rastreia HNSW em ciclos, aplica filtros inline",
    "    → Retoma travessia se LIMIT não for atingido",
    "Modos: off | strict_order | relaxed_order (recomendado)",
    "Exemplo SQL híbrido:",
    '  SELECT * FROM chunks WHERE tenant_id = X',
    '  ORDER BY embedding <=> $1 LIMIT 5',
], top=Inches(1.8), font_size=22)

# Slide 9: RAG
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_title(slide, "Arquitetura RAG")
add_body(slide, [
    "Fluxo completo:",
    "",
    "  1. Documento → fragmentação (chunking)",
    "  2. Cada chunk → embedding → armazena no pgvector",
    "  3. Pergunta do usuário → embedding → busca ANN",
    "  4. Chunks + pergunta → prompt → LLM → resposta",
    "",
    "Vantagens do PostgreSQL para RAG:",
    "  → Transação única: dado relacional + vetor",
    "  → Zero inconsistência (vs banco vetorial separado)",
    "  → Filtragem multi-tenant via RLS",
    "  → Backup/PITR unificado",
], top=Inches(1.8), font_size=24)

# Slide 10: Benchmarks
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_title(slide, "Benchmarks de Performance")
add_body(slide, [
    "100k vetores (384 dims, float32):",
    "  Busca exata:     48 ms    recall 100%  21 QPS",
    "  HNSW ef=40:      3 ms     recall 98.5% 325 QPS",
    "  HNSW ef=100:     4 ms     recall 99.7% 240 QPS",
    "  IVFFlat:         5.5 ms   recall 94%   180 QPS",
    "",
    "1M vetores (384 dims):",
    "  Busca exata:     650 ms    recall 100%  1.5 QPS",
    "  HNSW ef=40:      7 ms      recall 92%   142 QPS",
    "  HNSW ef=100:     15 ms     recall 98%   66 QPS",
    "  IVFFlat:         45 ms     recall 91.5% 22 QPS",
    "",
    "Fonte: pgvector benchmarks (Mastra, Supabase)",
], top=Inches(1.8), font_size=20)

# Slide 11: Configuração
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_title(slide, "Configuração do Ambiente")
add_body(slide, [
    "Parâmetros recomendados no postgresql.conf:",
    "",
    "  shared_buffers = 256MB         # Cache de blocos",
    "  effective_cache_size = 768MB   # Cache do sistema",
    "  work_mem = 64MB                # Ordenações por sessão",
    "  maintenance_work_mem = 4GB     # Compilação do HNSW",
    "  max_parallel_maintenance_workers = 4",
    "",
    "Dimensionamento do índice HNSW:",
    "  RAM_índice = 1.2 × (d × 4 + m × 8) × N",
    "  Ex: 1M vetores 384d → ~2.2 GB RAM",
],
    top=Inches(1.8), font_size=22)

# Slide 12: Demonstração
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_title(slide, "Demonstração Prática")
add_body(slide, [
    "Infraestrutura: Docker Compose + PostgreSQL 16 + pgvector",
    "Dados: 8 chunks sobre pgvector, embeddings all-MiniLM-L6-v2 (384d)",
    "",
    "Roteiro:",
    "  1. Schema: tabelas documents + document_chunks com vector(384)",
    "  2. Índices: HNSW (cosine) + GIN (tsvector) + B-Tree (tenant)",
    "  3. Inserção: generate_embeddings.py",
    "  4. Busca híbrida: hybrid_search.py (vetorial + full-text)",
    "  5. RAG pipeline: rag_pipeline.py",
    "",
    "Código disponível em: [link do repositório GitHub]",
], top=Inches(1.8), font_size=24)

# Slide 13: Referências
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_title(slide, "Referências")
add_body(slide, [
    "pgvector - Open-source vector similarity search for Postgres",
    "  https://github.com/pgvector/pgvector",
    "",
    "Malkov & Yashunin - HNSW (IEEE TPAMI, 2018)",
    "  https://arxiv.org/abs/1603.09320",
    "",
    "Supabase - HNSW Indexes in pgvector",
    "  https://supabase.com/docs/guides/ai/vector-indexes/hnsw-indexes",
    "",
    "Timescale - pgvectorscale",
    "  https://github.com/timescale/pgvectorscale",
    "",
    "Mastra - Benchmarking pgvector RAG performance",
    "  https://mastra.ai/blog/pgvector-perf",
    "",
    "PostgreSQL Documentation",
    "  https://www.postgresql.org/docs/",
], top=Inches(1.8), font_size=22)

# Salva
prs.save("slides/slides.pptx")
print("slides/slides.pptx gerado com sucesso!")
PYEOF
```

- [ ] **Step 2: Commit**

```bash
git add slides/slides.pptx
git commit -m "feat: add presentation slides (13 slides)"
```

---

### Task 10: PDF do Relatório

**Files:**
- Create: `docs/relatorio.pdf`

- [ ] **Step 1: Gerar PDF a partir do material existente**

```bash
# Usa o markdown existente como base, gera PDF
pip install weasyprint markdown
```

```python
"""
Gera PDF do relatório: material teórico + apêndices com código.
"""
import markdown
from weasyprint import HTML

with open("Otimização de pgvector no PostgreSQL.md") as f:
    md = f.read()

with open("demo/sql/01_schema.sql") as f:
    schema = f.read()
with open("demo/sql/02_queries.sql") as f:
    queries = f.read()

apendices = f"""
## Apêndice A — Código SQL

### Schema
```sql
{schema}
```

### Queries de Exemplo
```sql
{queries}
```
"""

html = markdown.markdown(
    md + "\n" + apendices,
    extensions=["fenced_code", "tables", "codehilite"],
)

css = """
body { font-family: serif; font-size: 12pt; line-height: 1.6; max-width: 210mm; margin: 0 auto; padding: 20mm; }
h1 { font-size: 24pt; color: #1a1a2e; }
h2 { font-size: 18pt; color: #1a1a2e; border-bottom: 1px solid #ccc; }
h3 { font-size: 14pt; color: #333; }
code { font-family: monospace; font-size: 10pt; background: #f4f4f4; padding: 2px 4px; border-radius: 3px; }
pre { background: #f4f4f4; padding: 12px; border-radius: 5px; overflow-x: auto; }
pre code { background: none; padding: 0; }
table { border-collapse: collapse; width: 100%; margin: 12px 0; }
th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
th { background: #1a1a2e; color: white; }
img { max-width: 100%; }
"""

HTML(string=f"<html><head><meta charset='utf-8'><style>{css}</style></head><body>{html}</body></html>") \\
    .write_pdf("docs/relatorio.pdf")

print("docs/relatorio.pdf gerado com sucesso!")
```

- [ ] **Step 2: Commit**

```bash
git add docs/relatorio.pdf
git commit -m "docs: add final report PDF with theory and code appendices"
```

---

### Task 11: README Raiz

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write README.md raiz**

```markdown
# PDB - Seminário: pgvector

**Disciplina:** DCT2202 - Projeto e Administração de Banco de Dados - T01 (2026.1)
**Professor:** Taciano de Morais Silva
**Centro:** CERES/UFRN
**Equipe:** José Inamar de Medeiros Júnior

## Tema
Administração e Otimização de Bancos de Dados Vetoriais para Aplicações de IA usando PostgreSQL (pgvector)

## Estrutura

```
├── slides/     — Slides da apresentação (PPTX)
├── demo/       — Código da demonstração prática (Docker + SQL + Python)
├── docs/       — Relatório PDF com material teórico + apêndices
└── proposta-seminario.md / .pdf
```

## Reprodução da Demo

```bash
cd demo
docker compose up -d
pip install -r src/requirements.txt
python src/generate_embeddings.py
python src/hybrid_search.py
python src/rag_pipeline.py
```
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add root README"
```

---

### Task 12: Push para GitHub

**Files:** Nenhum

- [ ] **Step 1: Criar repositório no GitHub (se não existir) e push**

```bash
# Verificar se remote existe
git remote -v

# Se não existir:
gh repo create pdb-seminario-vector-db --public --push --source=.
# Ou se remote já existe:
git push origin main
```

---

### Task 13: (Opcional) Copiar slides para Google Docs

Se quiser atender o requisito "link dos Slides no Google Docs com permissão de comentários", fazer upload manual do `slides/slides.pptx` para Google Drive → Google Slides.
