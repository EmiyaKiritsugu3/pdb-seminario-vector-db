# PDB - Seminario: pgvector

**Disciplina:** DCT2202 - Projeto e Administracao de Banco de Dados - T01 (2026.1)
**Professor:** Taciano de Morais Silva
**Centro:** CERES/UFRN
**Equipe:** Jose Inamar de Medeiros Junior

## Tema
Administracao e Otimizacao de Bancos de Dados Vetoriais para Aplicacoes de IA usando PostgreSQL (pgvector)

## Estrutura

```
slides/     - Slides da apresentacao (PPTX)
demo/       - Codigo da demonstracao pratica (Docker + SQL + Python)
docs/       - Relatorio PDF com material teorico + apendices
proposta-seminario.md / .pdf
```

## Reproducao da Demo

```bash
cd demo
docker compose up -d
pip install -r src/requirements.txt
python src/generate_embeddings.py
python src/hybrid_search.py
python src/rag_pipeline.py
```
