# Proposta de Seminário: Projeto de Banco de Dados

**Disciplina:** DCT2202 - Projeto e Administração de Banco de Dados - T01 (2026.1)
**Professor:** Taciano de Morais Silva
**Centro:** Centro de Ensino Superior do Seridó - CERES/UFRN

## Título/Tema
Administração e Otimização de Bancos de Dados Vetoriais para Aplicações de Inteligência Artificial

## Equipe
* José Inamar de Medeiros Júnior

## SGBD (Sistema de Gerenciamento de Banco de Dados)
**PostgreSQL (utilizando a extensão `pgvector`)**

O PostgreSQL é um robusto Sistema de Gerenciamento de Banco de Dados Objeto-Relacional (ORDBMS) de código aberto, amplamente reconhecido por sua confiabilidade, integridade de dados (conformidade ACID) e extensibilidade. Embora seja tradicionalmente utilizado para dados relacionais, sua arquitetura permite a integração de extensões poderosas. 

Para este seminário, o foco será no PostgreSQL equipado com a extensão **`pgvector`**. Esta extensão transforma o PostgreSQL em um banco de dados vetorial de alto desempenho, capaz de armazenar e consultar embeddings de alta dimensionalidade gerados por modelos de Inteligência Artificial (como LLMs). O `pgvector` permite a execução de buscas por similaridade utilizando métricas matemáticas diretas no banco de dados. Por exemplo, a similaridade de cosseno entre dois vetores $A$ e $B$ é calculada internamente como:

$$\text{similaridade}(A, B) = \frac{A \cdot B}{\|A\| \|B\|}$$

Ao utilizar o PostgreSQL, evitamos a necessidade de provisionar uma infraestrutura de banco de dados vetorial separada e dedicada, permitindo que dados relacionais (como informações de usuários ou metadados de projetos) coexistam e sejam consultados simultaneamente com dados vetoriais (embeddings semânticos).

## Proposta Prática
A apresentação abordará de forma explicativa o fluxo de **Retrieval-Augmented Generation (RAG)** para aplicações de Inteligência Artificial, com foco na administração e otimização de consultas vetoriais. Os seguintes tópicos serão abordados:

1. **Conceitos de Banco Vetorial:** O que são embeddings, como são gerados por modelos de IA e como bancos de dados vetoriais armazenam e consultam esses dados.
2. **pgvector no PostgreSQL:** Como a extensão `pgvector` transforma o PostgreSQL em um banco vetorial, permitindo buscas por similaridade usando operadores como `<=>` (distância de cosseno).
3. **Arquitetura RAG:** Explicação do fluxo RAG — como documentos são convertidos em embeddings, armazenados no banco e recuperados como contexto para responder consultas com LLMs.
4. **Otimização com índices HNSW:** Comparação conceitual entre busca exata (KNN) e busca aproximada (ANN), mostrando como os índices **HNSW (Hierarchical Navigable Small World)** melhoram o desempenho em grandes volumes de dados.

## Referências
* PostgreSQL Global Development Group. (2024). *PostgreSQL Documentation*. Recuperado de https://www.postgresql.org/docs/
* pgvector Contributors. (2024). *pgvector: Open-source vector similarity search for Postgres*. Recuperado de https://github.com/pgvector/pgvector
* Malkov, Y. A., & Yashunin, D. A. (2018). *Efficient and robust approximate nearest neighbor search using Hierarchical Navigable Small World graphs*. IEEE Transactions on Pattern Analysis and Machine Intelligence, 42(4), 824-836.
* Lewis, P., et al. (2020). *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*. Advances in Neural Information Processing Systems (NeurIPS).
