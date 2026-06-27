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
A demonstração prática focará na implementação de um fluxo de **Retrieval-Augmented Generation (RAG)** para uma aplicação de Inteligência Artificial, enfatizando a administração e a otimização das consultas vetoriais no banco de dados. As seguintes etapas serão realizadas:

1. **Configuração e Administração:** Instalação de uma instância do PostgreSQL e habilitação da extensão `pgvector`. Criação das tabelas relacionais contendo uma coluna do tipo vetor (`vector(n)`), onde *n* representa as dimensões do embedding de um modelo de IA de código aberto.
2. **Integração no Backend:** Desenvolvimento de um serviço backend (utilizando Go ou Python) que processa documentos de texto, interage com uma API de IA para gerar os embeddings e insere esses vetores no banco de dados.
3. **Busca por Similaridade:** Implementação de uma funcionalidade de busca onde uma consulta de texto (prompt do usuário) é convertida em um vetor, e o banco de dados executa uma busca de vizinhos mais próximos (K-Nearest Neighbors - KNN) utilizando operadores do `pgvector` (como `<=>` para distância de cosseno) para retornar os contextos mais relevantes.
4. **Otimização de Desempenho:** A demonstração prática culminará na otimização do banco de dados. Serão gerados milhares de registros para simular um ambiente de produção. Em seguida, compararemos o tempo de execução e o custo computacional de buscas exatas (sem índice) versus buscas aproximadas (Approximate Nearest Neighbor - ANN) através da criação e configuração de índices **HNSW (Hierarchical Navigable Small World)** no PostgreSQL.

## Referências
* PostgreSQL Global Development Group. (2024). *PostgreSQL Documentation*. Recuperado de https://www.postgresql.org/docs/
* pgvector Contributors. (2024). *pgvector: Open-source vector similarity search for Postgres*. Recuperado de https://github.com/pgvector/pgvector
* Malkov, Y. A., & Yashunin, D. A. (2018). *Efficient and robust approximate nearest neighbor search using Hierarchical Navigable Small World graphs*. IEEE Transactions on Pattern Analysis and Machine Intelligence, 42(4), 824-836.
* Lewis, P., et al. (2020). *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*. Advances in Neural Information Processing Systems (NeurIPS).
