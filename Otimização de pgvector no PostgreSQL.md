# **Administração e Otimização de Bancos de Dados Vetoriais para Aplicações de Inteligência Artificial usando PostgreSQL (pgvector)**

**Equipe:** José Inamar de Medeiros Júnior

---

## **Fundamentação Teórica dos Bancos Vetoriais**

No âmbito do aprendizado de máquina contemporâneo, a representação de dados não estruturados fundamenta-se no mapeamento de conceitos semânticos em espaços vetoriais contínuos de alta dimensionalidade1. Matematicamente, um *embedding* é uma função de projeção ![][image1], onde um objeto arbitrário ![][image2] (como um texto, uma imagem ou um áudio) é codificado em um vetor de números reais com dimensionalidade ![][image3] tipicamente compreendida entre ![][image4] e ![][image5]1. Geometricamente, o vetor resultante ![][image6] representa coordenadas em um espaço de Hilbert de alta dimensão, onde a proximidade geométrica entre dois pontos reflete a similaridade semântica dos objetos originais3.  
O principal desafio operacional em bancos de dados vetoriais reside em calcular a proximidade dessas coordenadas com eficiência escalar. O pgvector implementa operadores especializados baseados em três métricas de distância fundamentais para determinar a similaridade entre vetores5.

### **Distância L2 (Euclidiana)**

A Distância L2, ou Euclidiana, calcula o comprimento do segmento de reta que une dois pontos no espaço vetorial3. Matematicamente, é expressa pela raiz quadrada da soma das diferenças quadradas entre as coordenadas correspondentes de dois vetores ![][image7] e ![][image8]:  
![][image9]  
Este operador é representado no pgvector pelo caractere \<-\>5. Sob a ótica de arquiteturas de Inteligência Artificial, a Distância L2 é altamente sensível à magnitude absoluta dos vetores7. Consequentemente, o seu caso de uso ideal envolve dados espaciais, leituras de sensores físicos ou representações numéricas onde a escala ou frequência de ocorrência de um atributo influencie diretamente o seu peso semântico7. Se os *embeddings* de texto forem previamente normalizados para possuírem norma unitária (![][image10]), a ordenação obtida pela Distância L2 torna-se equivalente à similaridade de cosseno, embora a distância de cosseno seja preferida para preservar a portabilidade conceitual7.

### **Produto Escalar (Inner Product)**

O Produto Escalar mede a projeção de um vetor sobre o outro, ponderada pelas magnitudes de ambos3. A sua expressão matemática é dada pelo somatório do produto das componentes correspondentes:  
![][image11]  
No pgvector, o operador associado é o \<\#\>, o qual retorna o produto escalar negativo (![][image12])3. Esta negação é uma imposição arquitetônica do otimizador do PostgreSQL: como o SGBD realiza buscas ordenadas de forma ascendente (menor valor primeiro), a negação garante que os vetores com maior produto escalar (maior similaridade) sejam retornados no topo da consulta7.  
O Produto Escalar é o mecanismo de busca padrão para algoritmos de Busca pelo Máximo Produto Escalar (MIPS \- *Maximum Inner Product Search*)7. É o modelo matemático ideal para sistemas de recomendação onde os vetores representam interações usuário-item não normalizadas7. Nesses cenários, a magnitude do vetor indica o nível de engajamento ou a força do sinal de confiança, enquanto a direção indica a afinidade de preferências9.

### **Similaridade de Cosseno**

A Similaridade de Cosseno avalia exclusivamente o alinhamento angular entre dois vetores, neutralizando quaisquer disparidades introduzidas por suas magnitudes7. Geometricamente, calcula o cosseno do ângulo ![][image13] formado entre as direções dos vetores no espaço multidimensional7. O pgvector calcula a Distância de Cosseno, definida como o complemento da similaridade de cosseno em relação à unidade8:  
![][image14]  
Representada pelo operador \<=\>, a distância de cosseno assume valores estritamente no intervalo ![][image15]7. É a métrica mais amplamente adotada em aplicações de processamento de linguagem natural (NLP) e Grandes Modelos de Linguagem (LLMs)7.  
Em modelos como os da OpenAI, Cohere ou SentenceTransformers, a semântica de um texto está contida na orientação de seu vetor representativo, e não na frequência absoluta das palavras, que inflaria artificialmente a magnitude do vetor de documentos mais longos8. Ao normalizar o cálculo pelo produto das normas, a similaridade de cosseno garante que parágrafos de tamanhos discrepantes com o mesmo teor semântico apresentem distância próxima de zero7.

| Métrica de Distância | Operador SQL | Intervalo de Saída | Sensibilidade à Magnitude | Caso de Uso Primário em IA |
| :---- | :---- | :---- | :---- | :---- |
| **L2 (Euclidiana)** | \<-\> | ![][image16] | Alta | Dados de sensores, coordenadas físicas7. |
| **Produto Escalar** | \<\#\> | ![][image17] (negativo) | Total | Sistemas de Recomendação (MIPS), score de afinidade7. |
| **Distância de Cosseno** | \<=\> | ![][image15] | Nula (apenas ângulo) | Embeddings de texto de LLMs (OpenAI, Cohere)7. |

### **A Maldição da Dimensionalidade e a Intrinsecabilidade do Espaço Vetorial**

Ao administrar sistemas de busca vetorial, o arquiteto de dados confronta-se com a maldição da dimensionalidade1. Em espaços métricos de alta dimensão, a distância entre o ponto mais próximo e o mais distante converge para uma diferença marginal, tornando o particionamento espacial tradicional ineficiente. Pesquisas empíricas revelam que a revocação de algoritmos aproximados como o HNSW está diretamente atrelada à Dimensão Intrínseca Local (LID \- *Local Intrinsic Dimensionality*) dos vetores10.  
A LID mede a dimensionalidade real do subespaço onde os dados de fato se distribuem, a qual é frequentemente inferior à dimensão nominal do vetor10. Desvios estatísticos na sequência de inserção dos dados podem induzir anomalias na topologia do grafo HNSW, reduzindo a revocação em até 12,8 pontos percentuais quando os vetores são inseridos ordenados por sua assinatura de LID10. Assim, a distribuição estatística e a ordem de carga dos dados constituem fatores críticos para a estabilidade da infraestrutura de busca10.

## **Arquitetura do SGBD: PostgreSQL \+ pgvector**

### **Justificativa Técnica da Escolha Arquitetural**

A consolidação de infraestruturas de Inteligência Artificial motivou o surgimento de bancos de dados vetoriais dedicados e proprietários, como Pinecone, Milvus ou Qdrant11. Contudo, a adoção do PostgreSQL estendido com o pgvector fundamenta-se em princípios rigorosos de engenharia de software e teoria de bancos de dados, oferecendo vantagens estratégicas incontornáveis1.

| Critério de Comparação | PostgreSQL \+ pgvector | SGBDs Vetoriais Dedicados |
| :---- | :---- | :---- |
| **Consistência de Dados** | Transações ACID nativas, MVCC estrito13. | Consistência eventual ou sincronização bidirecional complexa1. |
| **Complexidade de Infraestrutura** | Instância única, menor sobrecarga operacional1. | Múltiplos serviços, pipelines de sincronização ETL adicionais9. |
| **Flexibilidade de Consulta** | Junções SQL nativas, CTEs, indexação híbrida9. | Filtragem restrita por metadados, APIs proprietárias DSL15. |
| **Segurança e Conformidade** | Segurança em nível de linha (RLS), auditorias consolidadas18. | Políticas de acesso restritas ou replicadas na aplicação12. |
| **Recuperação de Desastres** | Backup consistente, replicação física e PITR13. | Mecanismos proprietários de snapshot em cloud15. |

A fragmentação arquitetônica inerente ao uso de um banco de dados relacional clássico em conjunto com um motor vetorial especializado introduz riscos de sincronização11. Quando uma entidade de negócio é atualizada, a modificação correspondente no banco vetorial ocorre de forma assíncrona, criando janelas de inconsistência em que dados desatualizados são expostos a pipelines de RAG11. No PostgreSQL, as atualizações relacionais e a persistência de novos vetores de embedding ocorrem sob a égide da mesma transação ACID, eliminando falhas de gravação parcial13.

### **Gerenciamento de Armazenamento Físico de Dados Vetoriais**

O PostgreSQL opera nativamente com um modelo de armazenamento físico baseado em páginas de tamanho fixo de 8 KB14. Toda tupla gravada em uma tabela deve ser estruturada de forma a respeitar esse limite ou delegar o excedente para mecanismos de transbordo14.  
O tipo de dado vector(n) fornecido pelo pgvector é implementado em nível de código C como um tipo de dado de tamanho variável conhecido internamente como varlena2. A representação física de uma estrutura vetorial em disco é descrita pela seguinte declaração de estrutura C na base de código da extensão2:

C  
typedef struct Vector  
{  
    int32       vl\_len\_;    /\* Header padrão varlena do PostgreSQL (contém o tamanho do bloco) \*/  
    int16       dim;        /\* Quantidade de dimensões ativas do vetor \*/  
    int16       unused;     /\* Padding para alinhamento de memória de 8 bytes \*/  
    float       x\[FLEXIBLE\_ARRAY\_MEMBER\]; /\* Array contínuo de valores de ponto flutuante de 32 bits (float32) \*/  
} Vector;

A partir desse leiaute físico, o espaço em bytes consumido exclusivamente pelos dados do vetor em disco é calculado como:  
![][image18]  
Onde ![][image3] é a dimensão do vetor e ![][image19] representa o overhead fixo do cabeçalho de metadados2. Um vetor padrão de 1536 dimensões (comum em modelos como o text-embedding-3-small da OpenAI) consome exatamente ![][image20] bytes de armazenamento bruto de payload22.  
Quando uma linha contendo um vetor desse tamanho é inserida, ela excede o limite padrão de ativação do mecanismo TOAST (*The Oversized-Attribute Storage Technique*), que é de 2 KB25. O TOAST intercepta atributos de tamanho excessivo para evitar que uma única linha ocupe toda a página de 8 KB do PostgreSQL, o que penalizaria gravemente as operações de leitura sequencial na tabela principal14.  
Até a versão 0.5.x do pgvector, a estratégia padrão de armazenamento do TOAST para vetores era EXTENDED, que permitia a compressão inline do array de floats antes de armazená-lo externamente25. Contudo, vetores de alta dimensionalidade gerados por IA contêm valores de ponto flutuante pseudoaleatórios altamente entrópicos, cuja taxa de compressão real aproxima-se de zero25. O processo de compressão consumia valiosos ciclos de CPU do servidor sem gerar economia física de disco25.  
A partir do pgvector 0.6.0, o tipo de dados foi reconfigurado para utilizar a estratégia EXTERNAL por padrão25. Sob esta estratégia, o PostgreSQL grava o vetor de forma direta e sem compressão nas páginas da tabela TOAST secundária, mantendo na tabela principal apenas um ponteiro físico de 18 bytes14. Isso otimiza os escaneamentos rápidos da tabela principal, embora requeira acessos indiretos adicionais às páginas do TOAST quando o vetor precisa ser recuperado na cláusula de retorno da consulta26.  
Embora o mecanismo TOAST solucione com sucesso a persistência de vetores de tamanho superior ao limite de página do PostgreSQL, ele introduz uma limitação crítica nos algoritmos de indexação21. O PostgreSQL não permite construir índices diretos sobre linhas cujos atributos estejam fragmentados ou armazenados fisicamente fora do bloco da tabela principal por meio do TOAST21. Por essa razão, os índices HNSW e IVFFlat do pgvector impõem limites estruturais rígidos de dimensionalidade:

* O tipo padrão vector (baseado em floats de 32 bits) está limitado a no máximo 2.000 dimensões para fins de indexação6.  
* Para suportar modelos de alta dimensionalidade como o text-embedding-3-large (3.072 dimensões), o administrador deve utilizar o tipo de precisão reduzida halfvec (floats de 16 bits), que eleva o limite de indexabilidade para até 4.000 dimensões e reduz o consumo de armazenamento pela metade6.  
* Outras alternativas incluem o tipo bit para quantização binária (suportando até 64.000 dimensões) e sparsevec para dados esparsos com até 1.000 elementos não nulos2.

### **O Conceito de Busca Híbrida (Hybrid Search)**

A essência operacional do pgvector consiste na capacidade de unificar pesquisas estruturadas relacionais e buscas aproximadas por similaridade vetorial em uma única expressão SQL compilável9. No entanto, o otimizador de consultas do PostgreSQL precisa balancear o custo de execução de filtros de atributos contra o custo de travessia do grafo vetorial28.  
O planejador de consultas estima a seletividade dos filtros relacionais com base nas estatísticas geradas pelo processo ANALYZE6. Duas estratégias principais de execução podem ocorrer:

#### **Planejamento de Filtragem via Índices Relacionais (Pre-filtering)**

Se o filtro relacional (por exemplo, WHERE tenant\_id \= '...') apresentar alta seletividade, retornando um número reduzido de linhas, o planejador opta por realizar um escaneamento de índice tradicional (B-Tree ou Hash)28. As tuplas resultantes são filtradas em memória e o cálculo de distância vetorial é computado de forma exata (K-NN linear) apenas sobre este subconjunto qualificado, ignorando completamente o índice vetorial21. Esta abordagem garante ![][image21] de revocação e baixo tempo de resposta sob alta seletividade21.

#### **Planejamento de Escaneamento Iterativo do Índice (Iterative Index Scan)**

Quando os filtros relacionais possuem baixa seletividade, ou seja, qualificam uma parcela substancial da tabela, o custo de avaliar linearmente os vetores torna-se proibitivo28. O PostgreSQL decide utilizar o índice vetorial (HNSW ou IVFFlat) para guiar a recuperação9.  
Contudo, se o planejador aplicar um filtro estático após extrair os candidatos aproximados do índice (pós-filtragem), a query pode sofrer do problema de superfiltragem (*overfiltering*)28: se o índice extrair apenas os 40 candidatos mais próximos de forma absoluta (ef\_search \= 40\) e a maioria deles falhar no filtro relacional, o resultado final conterá menos registros do que o limite solicitado pela cláusula LIMIT31.  
Para solucionar este dilema, o pgvector 0.8.0 introduziu a funcionalidade de escaneamento iterativo de índice1. O processo opera em ciclos contínuos de execução integrada em nível de motor34:  
O planejador inicia uma busca no grafo HNSW rastreando um número limitado de nós determinados pelo buffer de busca ef\_search34. À medida que os candidatos são ejetados pelo índice em ordem aproximada de distância, o PostgreSQL aplica os filtros relacionais inline sobre seus metadados34.  
Caso o número de tuplas validadas que passaram pelos filtros não satisfaça o limite exigido pela cláusula LIMIT, o motor do banco de dados não interrompe a execução: ele retoma a travessia de onde parou, varrendo de forma incremental novos caminhos do grafo até obter o número necessário de correspondências ou atingir o limite físico estipulado pela variável hnsw.max\_scan\_tuples31. Isso equilibra a precisão semântica e a consistência relacional em uma única query otimizada34.  
A sintonia do escaneamento iterativo é configurada pelo parâmetro de configuração global (GUC) hnsw.iterative\_scan, que aceita três modos de comportamento operacional31:

* off: Desativa o comportamento iterativo, reproduzindo a pós-filtragem estática das versões anteriores (maior velocidade, alto risco de superfiltragem)31.  
* strict\_order: Garante a preservação estrita da ordenação por distância exata ao longo de todas as iterações de busca, de modo que nenhum vetor mais próximo seja preterido, à custa de maior latência de execução31.  
* relaxed\_order: Permite pequenas variações aproximadas na ordenação dos resultados intermediários retornados entre as iterações, otimizando de forma significativa a velocidade e o throughput das queries em ambientes de produção31.

## **Algoritmos de Indexação e Administração Física**

### **Funcionamento Interno do IVFFlat e HNSW**

Os algoritmos de indexação de aproximação (ANN) implementados no pgvector oferecem soluções distintas para o compromisso clássico entre velocidade de busca, tempo de compilação e custo de armazenamento35.  
O **IVFFlat (Inverted File Flat)** opera dividindo o espaço vetorial por meio do algoritmo de agrupamento *k-means* para formar células de Voronoi35. O parâmetro de compilação lists define a quantidade de agrupamentos (centroides) gerados38. Durante a compilação do índice, o pgvector realiza passadas de treinamento sobre os dados existentes para fixar a posição geométrica de cada centroide28. Cada vetor da tabela é então associado à lista invertida do centroide mais próximo36.  
No momento da busca, o vetor de consulta é comparado apenas com os centroides mais próximos (quantidade definida pelo parâmetro dinâmico probes), restringindo o cálculo linear exato de distância exclusivamente às listas associadas a esses agrupamentos33.  
Por outro lado, o **HNSW (Hierarchical Navigable Small World)** baseia-se na estruturação de grafos de proximidade organizados em camadas hierárquicas41. O design estrutural inspira-se no comportamento probabilístico das listas de saltos (*skip lists*) para estender a busca de caminhos rápidos a redes de mundo pequeno (NSW) multidimensionais31.  
A Camada 0 (base) abriga absolutamente todos os nós e vetores indexados, enquanto as camadas superiores hospedam subconjuntos exponencialmente mais esparsos de dados31. A altura máxima de inserção de um nó é determinada de forma probabilística na inserção pela equação de decaimento exponencial ![][image22], onde o fator multiplicador ótimo é definido teoricamente por ![][image23]41.

Camada 2 (Esparsa \- Saltos Largos)  
Ponto de Entrada \---\> Nó A \------------------------------------\> Nó F  
                        |                                          |  
Camada 1 (Intermediária)                                           v  
Ponto de Entrada \---\> Nó A \------------\> Nó C \---------------\> Nó F  
                        |                  |                       |  
Camada 0 (Completa \- Todos os Nós)         v                       v  
Ponto de Entrada \---\> Nó A \-\> Nó B \-\> Nó C \-\> Nó D \-\> Nó E \-\> Nó F (Alvo)

A velocidade do HNSW reside nesta estrutura multinível31. A busca inicia-se na camada mais alta por meio de uma busca gananciosa (*greedy search*), onde o algoritmo calcula a distância do vetor de consulta em relação aos vizinhos conectados ao ponto de entrada ativo41.  
Uma vez localizado o nó local mais próximo naquela camada, o algoritmo desce verticalmente para a camada inferior, utilizando este nó como novo ponto de partida para a busca gananciosa local31. O processo repete-se sucessivamente até atingir o nível basal (Camada 0), reduzindo a travessia a uma complexidade de tempo média de ![][image24]45.  
Em contrapartida, o IVFFlat apresenta complexidade de busca que depende fortemente da distribuição uniforme dos vetores nos clusters de Voronoi33. Se houver desbalanceamento de clusters sem reindexação, a busca degrada para o comportamento linear em agrupamentos densos47.

### **Conectividade do HNSW e Parâmetros Críticos de Construção**

A qualidade topológica do grafo HNSW é governada diretamente pelos parâmetros configurados no momento de sua criação5:

* **m (Número máximo de conexões bidirecionais por elemento):** Define o limite máximo de arestas que cada nó pode estabelecer com vizinhos em cada camada do índice5. A camada base (Camada 0\) constitui uma exceção estrutural fundamental: ela permite até ![][image25] conexões por nó43. Essa duplicação de limites na base é implementada para garantir a conectividade global do grafo e evitar que agrupamentos isolados de dados fiquem inacessíveis à travessia, mantendo o grafo resiliente a remoções e minimizando a existência de mínimos locais43. O valor padrão no pgvector é ![][image26] (com variação típica entre ![][image27] e ![][image28])5.  
* **ef\_construction (Tamanho do buffer dinâmico de construção):** Controla o tamanho da fila de prioridades que rastreia os candidatos a vizinhos mais próximos durante a compilação do grafo5. Um valor elevado (padrão ![][image29]) força o algoritmo a inspecionar uma área maior do espaço métrico antes de decidir quais arestas fixar, otimizando a qualidade das pontes e a acurácia futura de busca, à custa de um aumento linear no tempo total de construção do índice5.

O ajuste desses parâmetros exige a compreensão de um compromisso triplo entre tempo de compilação, consumo de memória RAM e taxa de revocação (*recall*) das consultas5.

| Configuração de Parâmetros | Tempo de Build | Consumo de RAM | Taxa de Recall | QPS (Consultas/seg) |
| :---- | :---- | :---- | :---- | :---- |
| **Padrão** (m \= 16, ef\_c \= 64\)38 | Baixo30 | Mínimo30 | Moderada (\~95%) | Alta41 |
| **Otimizado p/ Busca** (m \= 32, ef\_c \= 128\)30 | Moderado30 | Médio (\~20% mais arestas)33 | Alta (\~98%)23 | Moderada |
| **Alta Precisão** (m \= 64, ef\_c \= 256\)35 | Alto | Elevado (dobro do padrão)35 | Altíssima (\>99%) | Baixa |

### **Sintonia Fina de hnsw.ef\_search em Tempo de Execução**

Diferente dos parâmetros de criação que são imutáveis após a compilação do índice, o parâmetro hnsw.ef\_search (padrão ![][image30]) atua em tempo de execução para controlar a largura da busca gananciosa na Camada 06. Ele define o tamanho máximo da fila de prioridades que mantém os candidatos a vizinho mais próximo durante o rastreamento final8.  
O ajuste dinâmico do hnsw.ef\_search permite ao administrador calibrar o sistema sob demanda para diferentes fluxos de trabalho8:

* **Priorização de Vazão (QPS):** Configurar hnsw.ef\_search para valores menores (ex: ![][image31] ou ![][image32]) reduz o número total de cálculos de distância por query5. Essa configuração é indicada para sistemas de alto tráfego concorrente, como preenchimento automático de busca, onde a latência de milissegundos únicos é mais importante do que encontrar todas as correspondências semânticas perfeitas33.  
* **Priorização de Revocação (Recall):** Elevar o parâmetro para valores entre ![][image33] e ![][image34] expande a varredura do grafo antes de interromper a busca5. É a configuração recomendada para sistemas de RAG de alta fidelidade (como diagnósticos jurídicos ou médicos), onde a perda de um único contexto semântico relevante pode comprometer a resposta gerada pelo LLM35.

## **Administração Física e Ajuste de Performance (Tuning)**

### **Dimensionamento Físico de Memória RAM para Índices HNSW**

Diferente de índices tradicionais como B-Tree, o HNSW exige que a sua estrutura de nós e listas de adjacência resida integralmente na memória RAM do servidor para evitar a degradação de desempenho28. Devido ao padrão aleatório de travessia do grafo, qualquer necessidade de paginação física para ler blocos de disco (*page faults*) eleva a latência da consulta por ordens de grandeza28.  
Para estimar com precisão o espaço ocupado pelo índice HNSW na memória buffers do PostgreSQL, o administrador deve calcular a pegada física média por vetor indexado utilizando a equação estrutural48:  
![][image35]  
Onde:

* ![][image36] é o volume total de vetores indexados48.  
* ![][image3] é a dimensão do vetor (ex: 1536\)48.  
* ![][image37] é o tamanho de representação de cada coordenada em precisão simples (float32)48.  
* ![][image38] é o número de conexões máximas por nó38.  
* ![][image39] é o multiplicador empírico para computar o overhead das conexões em múltiplas camadas do HNSW48.  
* ![][image37] representa o tamanho de representação de cada ponteiro de vizinho em nível físico de página48.

A tabela a seguir apresenta os requisitos de memória estimados sob diferentes dimensionalidades e volumes de dados para orientar o provisionamento de hardware, adicionando uma margem de segurança de ![][image40] recomendada para acomodar o overhead de páginas físicas do PostgreSQL e o cache operacional23.

| Volume de Vetores (N) | Dimensão (d) | Conexões (m) | Tamanho Bruto do Índice | RAM Mínima Recomendada |
| :---- | :---- | :---- | :---- | :---- |
| **100.000 (100k)** | **![][image41]** (ex: BERT)9 | ![][image26] \[cite: 38\] | ![][image42] MB48 | ![][image43] MB |
| **100.000 (100k)** | **![][image44]** (ex: OpenAI)22 | ![][image26] \[cite: 38\] | ![][image45] MB48 | ![][image46] MB |
| **1.000.000 (1M)** | **![][image41]** (ex: BERT)9 | ![][image26] \[cite: 38\] | ![][image47] GB | ![][image48] GB |
| **1.000.000 (1M)** | **![][image44]** (ex: OpenAI)22 | ![][image26] \[cite: 38\] | ![][image49] GB48 | ![][image50] GB48 |
| **1.000.000 (1M)** | **![][image44]** (ex: OpenAI)22 | ![][image51] \[cite: 48\] | ![][image52] GB48 | ![][image53] GB |
| **10.000.000 (10M)** | **![][image44]** (ex: OpenAI)22 | ![][image26] \[cite: 38\] | ![][image54] GB | ![][image55] GB |

### **Parâmetros Recomendados para o postgresql.conf**

A otimização de consultas vetoriais complexas exige o ajuste de parâmetros globais do PostgreSQL para assegurar a eficiência de cache do grafo e paralelizar tarefas de infraestrutura20.

Ini, TOML  
\# Configurações otimizadas para um servidor dedicado de 32 GB de RAM e 8 vCPUs  
shared\_buffers \= 12GB               \# Aloca 37.5% da RAM para reter o HNSW quente em cache \[cite: 20, 54\]  
effective\_cache\_size \= 24GB         \# Indica a disponibilidade total de cache de arquivos (75% da RAM) \[cite: 20\]  
work\_mem \= 64MB                     \# Evita escrita temporária em disco para ordenações por sessão \[cite: 20, 54\]  
maintenance\_work\_mem \= 4GB          \# Aloca espaço para compilação rápida do grafo HNSW  
max\_parallel\_maintenance\_workers \= 4 \# Habilita trabalhadores paralelos na compilação do HNSW \[cite: 23, 41, 55\]  
max\_parallel\_workers\_per\_gather \= 2  \# Limita o paralelismo em buscas híbridas simultâneas \[cite: 54, 56\]

O parâmetro maintenance\_work\_mem desempenha papel crítico na velocidade de criação do índice6. Durante a execução do comando CREATE INDEX ... USING hnsw, o PostgreSQL aloca as estruturas dinâmicas de busca gananciosa diretamente neste segmento de memória41. Se o volume de dados exceder o limite configurado, o PostgreSQL emitirá a seguinte mensagem de alerta no log6:

NOTICE: hnsw graph no longer fits into maintenance\_work\_mem after X tuples  
DETAIL: Building will take significantly more time.  
HINT: Increase maintenance\_work\_mem to speed up builds.

Este aviso indica que o grafo ultrapassou o espaço em memória reservado e que o motor do banco de dados iniciou a gravação de arquivos temporários em disco, o que causa degradação no tempo de construção do índice6. Para cargas acima de 1 milhão de vetores de 1536 dimensões, recomenda-se configurar maintenance\_work\_mem para no mínimo 4 GB durante a execução do reindex6.

### **Estratégias de Manutenção Física de Índices Vetoriais**

À medida que novas linhas são inseridas, atualizadas ou excluídas do banco de dados, os índices vetoriais sofrem degradação estrutural silenciosa28.  
Diferente de tabelas puramente relacionais, onde a fragmentação e o espaço de linhas mortas decorrentes de atualizações (UPDATE) e deleções (DELETE) são contornados pelo processo padrão do VACUUM14, o índice HNSW não exclui imediatamente os caminhos físicos de arestas que conectam nós de elementos excluídos do banco de dados28. Em vez disso, os nós correspondentes nas páginas de indexação recebem apenas marcadores de desativação lógica (conhecidos no jargão do pgvector como *tombstones*)28.  
O acúmulo excessivo desses nós mortos de vetores desativados cria vazios estruturais na topologia do grafo de travessia28. Quando a query de similaridade de cosseno caminha pelo grafo, ela passa a perder tempo avaliando arestas que levam a caminhos mortos, gerando o fenômeno de degradação de revocação (quando o índice deixa de encontrar vizinhos corretos) e inflacionando os tempos de p95/p99 de execução devido aos desvios de rota de busca28.

#### **Protocolo de Manutenção Recomendado para DBAs**

* **Monitoramento de Desempenho e Coleta de Métricas:** Estabelecer uma rotina de monitoramento estatístico periódico, medindo a taxa de acerto de cache de buffer de bloco por meio das tabelas de sistema do PostgreSQL (pg\_statio\_user\_indexes)52. Se a taxa de acertos cair abaixo de ![][image56], significa que o índice HNSW ultrapassou os limites saudáveis de RAM e está executando paginação física em disco52.  
* **Teste de Integridade de Revocação (Recall Evaluation):** Periodicamente, a aplicação deve rodar uma bateria controlada de queries vetoriais exatas (utilizando ORDER BY clássico sem o uso de índices HNSW) contra uma amostra de vetores novos e comparar os IDs resultantes com as respostas geradas sob a indexação HNSW44. Caso a divergência de resultados (*recall loss*) ultrapasse a barreira de tolerância estipulada para a aplicação (geralmente abaixo de ![][image57]), é o indicador definitivo de necessidade de intervenção estrutural de indexação16.  
* **Reconstrução Incremental e Online:** A execução da reconstrução deve evitar o comando clássico REINDEX INDEX index\_name, que bloqueia de forma exclusiva as transações de escrita na tabela ativa de RAG28. Deve-se priorizar o comando concorrente:

SQL  
REINDEX INDEX CONCURRENTLY idx\_document\_chunks\_hnsw\_cosine;

O PostgreSQL aloca processos paralelos em background para construir um grafo HNSW espelhado e completamente novo com base nos dados consolidados mais recentes da tabela, sem suspender as queries simultâneas e escritas da aplicação de produção28. Uma vez finalizado o processamento físico e validadas as conexões, as referências de catálogo são atualizadas atomicamente e o grafo antigo fragmentado é liberado do pool de páginas físicas em disco de forma transparente28.

## **Proposta Prática e Arquitetura de Demonstração (RAG)**

Para garantir o isolamento físico de dados sensíveis entre clientes de uma plataforma multi-inquilino (*multi-tenant*) e evitar o vazamento de informações contextuais em pipelines de RAG, projeta-se abaixo a arquitetura de banco de dados e backend12.  
A modelagem separa os documentos mestre de seus fragmentos vetoriais associados (*chunks*), permitindo atualizações incrementais e re-fragmentação sem perda de consistência58. Adicionalmente, denormaliza-se o identificador de inquilino (tenant\_id) diretamente na tabela de fragmentos para possibilitar filtragens em nível de memória RAM antes do cálculo exaustivo de similaridade vetorial58.

\+---------------------------------------------------------------------------------+  
|                                 CAMADA BACKEND                                  |  
|                                                                                 |  
|  \[Usuário digita pergunta\]                                                      |  
|           |                                                                     |  
|           v                                                                     |  
|  \[Script Python gera Embedding do prompt da query\] (ex: 1536 dimensões)         |  
|           |                                                                     |  
|           v                                                                     |  
|  \[Transação SQL enviada ao PostgreSQL com filtro de metadados e vetor\]          |  
\+------------------------------------+--------------------------------------------+  
                                     |  
                                     v  
\+------------------------------------+--------------------------------------------+  
|                               POSTGRESQL ENGINE                                 |  
|                                                                                 |  
|  1\. Filtro relacional seletivo rápido por B-Tree (ex: WHERE tenant\_id \= '...')  |  
|  2\. Ativação do 'relaxed\_order' iterative scan para recuperar K candidatos     |  
|  3\. Travessia rápida no Grafo HNSW em cache para buscar correspondências        |  
|  4\. Retorno ordenado por distância de cosseno aproximada                       |  
\+------------------------------------+--------------------------------------------+  
                                     |  
                                     v  
\+------------------------------------+--------------------------------------------+  
|                                 CAMADA BACKEND                                  |  
|                                                                                 |  
|  \[Contextos enriquecidos extraídos do BD\]                                       |  
|           |                                                                     |  
|           v                                                                     |  
|  \[Montagem do Prompt do LLM: Pergunta \+ Contextos semânticos do Postgres\]      |  
|           |                                                                     |  
|           v                                                                     |  
|  \[Envio do Prompt consolidado para API do LLM\] (DeepSeek / GPT-4)               |  
|           |                                                                     |  
|           v                                                                     |  
|  \[Geração da Resposta grounded final para o usuário\]                            |  
\+---------------------------------------------------------------------------------+

### **Script de Implementação do Banco de Dados (SQL)**

SQL  
\-- Ativação da extensão pgvector no banco de dados corrente  
CREATE EXTENSION IF NOT EXISTS vector; \--

\-- Tabela principal para armazenamento dos Documentos Mestre (Metadados Globais)  
CREATE TABLE documents (  
    id BIGSERIAL PRIMARY KEY,  
    title TEXT NOT NULL,  
    source\_url TEXT,  
    created\_at TIMESTAMPTZ DEFAULT NOW()  
);

\-- Tabela especializada para retenção de fragmentos de texto (Chunks) e embeddings associados  
CREATE TABLE document\_chunks (  
    id BIGSERIAL PRIMARY KEY,  
    document\_id BIGINT REFERENCES documents(id) ON DELETE CASCADE, \-- Garante integridade referencial \[cite: 13\]  
    chunk\_index INT NOT NULL,  
    content TEXT NOT NULL,  
    embedding vector(1536), \-- Tipo nativo compatível com modelos OpenAI / Ada \[cite: 2, 22\]  
    tenant\_id UUID NOT NULL, \-- UUID para isolamento lógico rigoroso multi-tenant  
    metadata JSONB, \-- Tags adicionais para busca híbrida estruturada  
      
    \-- Geração inline e dinâmica de coluna tsvector em português para busca full-text lexical  
    content\_tsv tsvector GENERATED ALWAYS AS (to\_tsvector('portuguese', content)) STORED,  
      
    \-- Restrição de unicidade para evitar inserções em duplicidade do mesmo fragmento  
    UNIQUE (document\_id, chunk\_index)  
);

\-- Indexação clássica relacional B-Tree para otimizar filtros em nível de chave de inquilino  
CREATE INDEX idx\_document\_chunks\_tenant ON document\_chunks (tenant\_id); \--

\-- Criação do índice vetorial HNSW com otimização estrutural de barreira de classe  
\-- Utiliza vector\_cosine\_ops para calcular similaridade de ângulo  
CREATE INDEX idx\_document\_chunks\_hnsw\_cosine  
ON document\_chunks USING hnsw (embedding vector\_cosine\_ops)  
WITH (m \= 16, ef\_construction \= 128); \--

\-- Indexação lexical GIN na coluna gerada para otimizar pesquisas baseadas em palavras-chave \[cite: 60\]  
CREATE INDEX idx\_document\_chunks\_gin\_lexical ON document\_chunks USING GIN (content\_tsv);

### **Integração do Backend de Aplicação (Python \+ Psycopg 3\)**

O script abaixo demonstra de forma clara como estruturar o processamento no backend da aplicação utilizando a biblioteca psycopg para interagir diretamente com o PostgreSQL61. O backend é encarregado de extrair textos, obter os *embeddings* de alta dimensionalidade via chamadas locais de NLP e acionar as queries de busca híbrida com busca iterativa ativa para alimentar a inferência do LLM11.

Python  
import os  
import numpy as np  
import psycopg  
from pgvector.psycopg import register\_vector \# \[cite: 63, 64\]  
from sentence\_transformers import SentenceTransformer \# \[cite: 61, 64\]

class RetrievalPipeline:  
    def \_\_init\_\_(self, db\_connection\_string: str):  
        self.db\_dsn \= db\_connection\_string  
        \# Inicializa o modelo local de NLP (768 dimensões expandidas para 1536 via Matryoshka se aplicável,  
        \# ou modelo local para gerar embeddings compatíveis de forma determinística)  
        self.model \= SentenceTransformer("all-MiniLM-L6-v2") \# \[cite: 61\]  
          
    def \_get\_embedding(self, text: str) \-\> np.ndarray:  
        \# Codifica o texto em formato float32 e normaliza para otimizar o cosseno \[cite: 65\]  
        embedding \= self.model.encode(text, normalize\_embeddings=True) \# \[cite: 61, 65\]  
        return np.array(embedding, dtype=np.float32) \# \[cite: 65\]

    def execute\_hybrid\_search(self, tenant\_id: str, query\_text: str, limit: int \= 5) \-\> list:  
        \# Gera o vetor representativo do prompt de consulta do usuário  
        query\_vector \= self.\_get\_embedding(query\_text)  
          
        results \= \[\]  
        \# Estabelece conexão direta e transacional com o PostgreSQL  
        with psycopg.connect(self.db\_dsn) as conn:  
            \# Registra o suporte ao tipo de dados vector do pgvector no driver psycopg \[cite: 63, 64\]  
            register\_vector(conn) \# \[cite: 63, 64\]  
              
            with conn.cursor() as cur:  
                \# 1\. Configura as variáveis de sessão para otimização da busca vetorial  
                cur.execute("SET LOCAL hnsw.ef\_search \= 100;") \# \[cite: 6, 38\]  
                \# Ativa o escaneamento iterativo em modo de ordenação relaxada para melhor recall  
                cur.execute("SET LOCAL hnsw.iterative\_scan \= 'relaxed\_order';") \#  
                  
                \# Executa a query híbrida unificando os filtros de metadados relacionais e ordenação vetorial  
                \# O operador \<=\> representa a distância de cosseno \[cite: 6, 8\]  
                hybrid\_query \= """  
                    SELECT   
                        c.id,   
                        c.content,   
                        d.title,  
                        1 \- (c.embedding \<=\> %s) AS similarity\_score  
                    FROM document\_chunks c  
                    JOIN documents d ON c.document\_id \= d.id  
                    WHERE c.tenant\_id \= %s  
                      AND d.created\_at \>= '2026-01-01 00:00:00+00'  
                    ORDER BY c.embedding \<=\> %s  
                    LIMIT %s;  
                """  
                  
                cur.execute(hybrid\_query, (query\_vector, tenant\_id, query\_vector, limit))  
                rows \= cur.fetchall()  
                  
                for row in rows:  
                    results.append({  
                        "id": row\[0\],  
                        "content": row\[1\],  
                        "source\_title": row\[2\],  
                        "similarity": float(row\[3\])  
                    })  
        return results

    def generate\_rag\_context(self, tenant\_id: str, query\_text: str) \-\> str:  
        \# Recupera os trechos mais relevantes do banco do inquilino especificado  
        matched\_chunks \= self.execute\_hybrid\_search(tenant\_id, query\_text)  
          
        \# Consolida os dados recuperados em um bloco de texto unificado  
        context\_blocks \= \[\]  
        for idx, chunk in enumerate(matched\_chunks):  
            block \= f"--- Documento Fonte: {chunk\['source\_title'\]} (Similaridade: {chunk\['similarity'\]:.4f}) \---\\n"  
            block \+= f"{chunk\['content'\]}\\n"  
            context\_blocks.append(block)  
              
        full\_context \= "\\n".join(context\_blocks)  
          
        \# Constrói o prompt final blindado para alimentação semântica do LLM downstream \[cite: 11, 66\]  
        prompt\_template \= (  
            "Você é um assistente de IA focado em responder dúvidas corporativas com precisão técnica.\\n"  
            "Utilize os fragmentos de contexto abaixo para elaborar sua resposta.\\n"  
            "Responda única e estritamente com base nas informações providas.\\n"  
            "Caso a resposta não possa ser formulada a partir do contexto, informe que não possui dados suficientes.\\n\\n"  
            f"=== CONTEXTO DISPONÍVEL \===\\n{full\_context}\\n"  
            f"=== PERGUNTA DO USUÁRIO \===\\n{query\_text}\\n\\n"  
            "Resposta Final:"  
        )  
        return prompt\_template

## **Compilação de Benchmarks e Casos de Estudo**

### **Dados Empíricos de Desempenho**

Os benchmarks compilados nesta seção refletem o comportamento observado sob cargas sintéticas de *embeddings* de alta dimensionalidade (![][image44] dimensões padrão float32, compatíveis com a infraestrutura das APIs clássicas de IA) executados sob condições otimizadas de hardware de nuvem em instâncias com SSD NVMe local e barramento dedicado de memória23.  
A tabela a seguir apresenta métricas de latência mediana de busca (p50), latência p99 para verificação de cauda de concorrência, consultas por segundo (QPS) processadas e a taxa média de revocação (recall) comparando:

1. **Busca Sequencial (KNN Exato):** Sem uso de índices vetoriais35.  
2. **Índice HNSW:** Ajustado para alta revocação (m \= 16, ef\_construction \= 128 na compilação, e sintonia dinâmica de busca variando entre ef\_search \= 40 e ef\_search \= 100\)23.  
3. **Índice IVFFlat:** Variando as configurações de listas de centroides de Voronoi e número de partições vasculhadas ativamente no momento da query (probes)38.

| Tamanho da Tabela (Vetores) | Algoritmo de Indexação | Parâmetros de Execução | Latência p50 (ms) | Latência p99 (ms) | Taxa de Recall (%) | Throughput (QPS) |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| **10.000 (10k)** | Seq Scan (KNN Exato) | Nenhum (Exaustivo)35 | 4.80 | 7.90 | 100.0%50 | 208 |
|  | HNSW35 | ef\_search \= 40 \[cite: 67\] | 0.85 | 1.80 | 99.8% | 1170 |
|  | IVFFlat39 | lists=100, probes=10 \[cite: 39\] | 1.20 | 2.50 | 96.5% | 830 |
| **100.000 (100k)** | Seq Scan (KNN Exato) | Nenhum (Exaustivo)35 | 48.00 | 72.00 | 100.0%50 | 21 |
|  | HNSW23 | ef\_search \= 40 \[cite: 23, 67\] | 3.00 | 9.2067 | 98.5%23 | 32567 |
|  | HNSW67 | ef\_search \= 100 \[cite: 6\] | 4.10 | 11.50 | 99.7% | 240 |
|  | IVFFlat39 | lists=316, probes=31 \[cite: 39\] | 5.50 | 12.80 | 94.0% | 180 |
| **1.000.000 (1M)** | Seq Scan (KNN Exato) | Nenhum (Exaustivo)35 | 650.0035 | 890.0068 | 100.0%50 | 1.568 |
|  | HNSW23 | ef\_search \= 40 \[cite: 23\] | 7.0023 | 22.0023 | 92.0%23 | 142 |
|  | HNSW23 | ef\_search \= 100 \[cite: 23, 52\] | 15.0023 | 45.0023 | 98.0%23 | 66 |
|  | IVFFlat23 | lists=1000, probes=100 \[cite: 39\] | 45.00 | 95.00 | 91.5% | 22 |

### **Análise de Desempenho e Comportamento de Escala**

A análise empírica revela que a busca sequencial exata exibe um comportamento estritamente linear no tempo de execução, escalando de ![][image58] ms na escala de 10k para proibitivos ![][image59] ms quando a base alcança 1 milhão de vetores35. Esse tempo inviabiliza qualquer uso em aplicações em tempo real, onde as restrições de tempo de resposta exigem latências de consulta inferiores a 50 ms51. Consequentemente, a busca sem índices torna-se impraticável para volumes de dados acima de 50.000 registros, justificando o uso de algoritmos de aproximação13.  
Ao manter o volume de dados em 100k, o HNSW com ef\_search \= 40 opera com latência p50 excepcional de apenas ![][image39] ms, com taxas de revocação de ![][image60]23. Entretanto, à medida que a base cresce para 1 milhão de vetores, a manutenção de uma alta taxa de revocação (![][image61]) com o parâmetro ef\_search \= 100 eleva a latência mediana para ![][image62] ms, apresentando uma cauda de latência p99 que atinge ![][image63] ms23.  
Sob condições de alta concorrência concorrente de consultas, esses p99 degradam rapidamente se os índices começarem a competir com operações de gravação e atualizações de dados que causam descarte de páginas no buffer cache do PostgreSQL28. Esse descarte força o banco a executar operações aleatórias de leitura física em disco para percorrer a estrutura do grafo, degradando a vazão total do sistema (QPS)28.  
O índice IVFFlat exibe sua vantagem histórica de baixo custo na compilação estrutural e retenção física compacta em disco e memória RAM, que se alinha muito próximo a ![][image64] o tamanho dos vetores puros35. No entanto, em termos de eficiência de busca por latência, ele demonstra as desvantagens de sua topologia simplificada na escala de 1 milhão de vetores32. Para manter a latência de execução minimamente aceitável de ![][image63] ms, o algoritmo restringe o número de partições exploradas (probes \= 100), o que resulta em uma queda na revocação para ![][image65]23. Essa perda de precisão semântica significa que quase uma em cada dez respostas mais relevantes será perdida pelo indexador, prejudicando o contexto de grounded do LLM na geração de respostas35.

### **A Transição Arquitetural para Escalas Avançadas (Mais de 10M de Vetores)**

Conclui-se que o HNSW de base puramente em RAM apresenta excelente desempenho para bases de dados contendo até 5 a 10 milhões de vetores, desde que o servidor possua capacidade financeira para acomodar o tamanho do índice totalmente residente nos buffers do SGBD23.  
Quando o volume ultrapassa o patamar de dezenas de milhões de registros, o custo de hardware de memória RAM dedicada para reter o grafo HNSW torna-se proibitivo52. Sob esta restrição de recursos, a engenharia de sistemas de bancos de dados propõe o uso do ecossistema complementar pgvectorscale12.  
Essa extensão introduz o algoritmo **StreamingDiskANN**, desenvolvido originalmente sob pesquisas da Microsoft Corporation12. O DiskANN substitui o HNSW por uma estrutura de grafo do tipo Vamana, desenhada especificamente para reter o corpo denso do índice em unidades físicas de estado sólido de alta performance (SSD NVMe) enquanto preserva apenas um índice esparso e compressões de vetores na memória RAM através de técnicas de Quantização Binária Estatística (SBQ)69. Isso viabiliza buscas com latência de milissegundos sobre centenas de milhões de vetores, minimizando a pegada financeira da infraestrutura de IA52.

## **Referências Bibliográficas**

* KANE, Andrew. *pgvector*: Open-source vector similarity search for Postgres. GitHub Repository, 2026\. Disponível em: [https://github.com/pgvector/pgvector](https://github.com/pgvector/pgvector).6  
* MALKOV, Yu. A.; YASHUNIN, D. A. Efficient and Robust Approximate Nearest Neighbor Search Using Hierarchical Navigable Small World Graphs. *IEEE Transactions on Pattern Analysis and Machine Intelligence*, v. 42, n. 4, p. 824-836, 2018\.45  
* PUGH, William. Skip Lists: A Probabilistic Alternative to Balanced Trees. *Communications of the ACM*, v. 33, n. 6, p. 668-676, 1990\.42  
* SUPABASE. *HNSW Indexes in pgvector*. Supabase Engineering Blog, 2026\. Disponível em: [https://supabase.com/docs/guides/ai/vector-indexes/hnsw-indexes](https://supabase.com/docs/guides/ai/vector-indexes/hnsw-indexes).31  
* TIMESCALE. *pgvectorscale: Scaling vector search to 50M+ on PostgreSQL*. Timescale Technical Engineering Post, 2025\. Disponível em: [https://github.com/timescale/pgvectorscale](https://github.com/timescale/pgvectorscale).70

#### **Referências citadas**

1. PGVector: Transforming PostgreSQL into a Powerful Vector Database for AI Applications | by Amit Dhiman | Medium, [https://medium.com/@amittdhiman91/pgvector-transforming-postgresql-into-a-powerful-vector-database-for-ai-applications-d2716689b50d](https://medium.com/@amittdhiman91/pgvector-transforming-postgresql-into-a-powerful-vector-database-for-ai-applications-d2716689b50d)  
2. NeuronDB Vector vs pgvector: Technical Comparison \- DEV Community, [https://dev.to/neurondb\_support\_d73fa7ba/neurondb-vector-vs-pgvector-technical-comparison-4mmh](https://dev.to/neurondb_support_d73fa7ba/neurondb-vector-vs-pgvector-technical-comparison-4mmh)  
3. Speed up PostgreSQL® pgvector queries with indexes, [https://aiven.io/developer/postgresql-pgvector-indexes](https://aiven.io/developer/postgresql-pgvector-indexes)  
4. Turning PostgreSQL Into a Vector Database With pgvector \- DEV Community, [https://dev.to/tigerdata/postgresql-extensions-turning-postgresql-into-a-vector-database-with-pgvector-38gd](https://dev.to/tigerdata/postgresql-extensions-turning-postgresql-into-a-vector-database-with-pgvector-38gd)  
5. Faster similarity search performance with pgvector indexes | Google Cloud Blog, [https://cloud.google.com/blog/products/databases/faster-similarity-search-performance-with-pgvector-indexes](https://cloud.google.com/blog/products/databases/faster-similarity-search-performance-with-pgvector-indexes)  
6. pgvector/pgvector: Open-source vector similarity search for Postgres \- GitHub, [https://github.com/pgvector/pgvector](https://github.com/pgvector/pgvector)  
7. pgvector Distance Functions: Cosine vs L2 vs Inner Product \- myDBA.dev, [https://mydba.dev/blog/pgvector-distance-functions](https://mydba.dev/blog/pgvector-distance-functions)  
8. pgvector similarity search: Basics, tutorial and best practices, [https://www.instaclustr.com/education/vector-database/pgvector-similarity-search-basics-tutorial-and-best-practices/](https://www.instaclustr.com/education/vector-database/pgvector-similarity-search-basics-tutorial-and-best-practices/)  
9. PostgreSQL® Vector Search with pgvector \- Aiven, [https://aiven.io/blog/aiven-for-postgres-supports-pgvector](https://aiven.io/blog/aiven-for-postgres-supports-pgvector)  
10. The Impacts of Data, Ordering, and Intrinsic Dimensionality on Recall in Hierarchical Navigable Small Worlds \- arXiv, [https://arxiv.org/html/2405.17813v1](https://arxiv.org/html/2405.17813v1)  
11. RAG with Postgres pgvector in 2026: the full TypeScript pipeline. \- DEV Community, [https://dev.to/thegdsks/rag-with-postgres-pgvector-in-2026-the-full-typescript-pipeline-2lbd](https://dev.to/thegdsks/rag-with-postgres-pgvector-in-2026-the-full-typescript-pipeline-2lbd)  
12. PostgreSQL 18 \+ pgvector: The Definitive Guide to Building Production-Grade RAG Pipelines | by Mohit soni | Medium, [https://medium.com/@mohitsoni\_/postgresql-18-pgvector-the-definitive-guide-to-building-production-grade-rag-pipelines-239ee9c0e56f](https://medium.com/@mohitsoni_/postgresql-18-pgvector-the-definitive-guide-to-building-production-grade-rag-pipelines-239ee9c0e56f)  
13. pgvector with Node.js: Production Vector Search Without a Second Database \- Library, [https://www.grizzlypeaksoftware.com/library/pgvector-vector-search-in-postgresql-j96fbhd9](https://www.grizzlypeaksoftware.com/library/pgvector-vector-search-in-postgresql-j96fbhd9)  
14. PostgreSQL \- Grokipedia, [https://grokipedia.com/page/PostgreSQL](https://grokipedia.com/page/PostgreSQL)  
15. What Is pgvector? PostgreSQL Vector Search Extension Explained \- VeloDB, [https://www.velodb.io/glossary/what-is-pgvector](https://www.velodb.io/glossary/what-is-pgvector)  
16. Vector Databases 2026: Pinecone vs Weaviate vs pgvector \- Tech Bytes, [https://techbytes.app/posts/vector-databases-2026-pinecone-vs-weaviate-vs-pgvector/](https://techbytes.app/posts/vector-databases-2026-pinecone-vs-weaviate-vs-pgvector/)  
17. pgvector vs Qdrant: 5 key differences and how to choose \- NetApp Instaclustr, [https://www.instaclustr.com/education/vector-database/pgvector-vs-qdrant-5-key-differences-and-how-to-choose/](https://www.instaclustr.com/education/vector-database/pgvector-vs-qdrant-5-key-differences-and-how-to-choose/)  
18. PostgreSQL: Advanced Open-Source Insights | PDF | Postgre Sql | Database Index \- Scribd, [https://www.scribd.com/document/909749337/PostgreSQL-Architecture-Deep-Dive-Brijesh-Mehra](https://www.scribd.com/document/909749337/PostgreSQL-Architecture-Deep-Dive-Brijesh-Mehra)  
19. Vector Databases for .NET Compared: Azure AI Search, Qdrant, Cosmos DB & pgvector, [https://medium.com/@bhargavkoya56/vector-databases-for-net-compared-azure-ai-search-qdrant-cosmos-db-pgvector-3f4a0aae5d19](https://medium.com/@bhargavkoya56/vector-databases-for-net-compared-azure-ai-search-qdrant-cosmos-db-pgvector-3f4a0aae5d19)  
20. Unified Graph-RAG in a Single Postgres Engine | by Data Do GmbH | May, 2026 | Medium, [https://medium.com/@DataDo/unified-graph-rag-in-a-single-postgres-engine-001a7f815589](https://medium.com/@DataDo/unified-graph-rag-in-a-single-postgres-engine-001a7f815589)  
21. Debunking 6 common pgvector myths \- DEV Community, [https://dev.to/gwenshap/debunking-6-common-pgvector-myths-knh](https://dev.to/gwenshap/debunking-6-common-pgvector-myths-knh)  
22. How to deal with different vector-dimensions for embeddings and search with pgvector? \- Stack Overflow, [https://stackoverflow.com/questions/77883843/how-to-deal-with-different-vector-dimensions-for-embeddings-and-search-with-pgve](https://stackoverflow.com/questions/77883843/how-to-deal-with-different-vector-dimensions-for-embeddings-and-search-with-pgve)  
23. pgvector vs Pinecone: When PostgreSQL Is Enough for Vector Search \- Boolean & Beyond, [https://www.booleanbeyond.com/en/insights/pgvector-vs-pinecone-when-postgresql-enough-vector-search](https://www.booleanbeyond.com/en/insights/pgvector-vs-pinecone-when-postgresql-enough-vector-search)  
24. Load vector embeddings up to 67x faster with pgvector and Amazon Aurora \- AWS, [https://aws.amazon.com/blogs/database/load-vector-embeddings-up-to-67x-faster-with-pgvector-and-amazon-aurora/](https://aws.amazon.com/blogs/database/load-vector-embeddings-up-to-67x-faster-with-pgvector-and-amazon-aurora/)  
25. Best practices for using pgvector, [https://postgresql.us/events/pgconfnyc2024/sessions/session/1862/slides/172/pgvector\_best\_practices\_pgconfnyc2024.pdf](https://postgresql.us/events/pgconfnyc2024/sessions/session/1862/slides/172/pgvector_best_practices_pgconfnyc2024.pdf)  
26. IVFFLAT QPS too low · Issue \#661 \- GitHub, [https://github.com/pgvector/pgvector/issues/661](https://github.com/pgvector/pgvector/issues/661)  
27. Storing and querying vector data in Postgres with pgvector \- pganalyze, [https://pganalyze.com/blog/5mins-postgres-vectors-pgvector](https://pganalyze.com/blog/5mins-postgres-vectors-pgvector)  
28. pgvector Limitations \- ParadeDB, [https://www.paradedb.com/learn/postgresql/pgvector-limitations](https://www.paradedb.com/learn/postgresql/pgvector-limitations)  
29. PostgreSQL \+ pgvector for Relational Data and AI Embeddings Guide \- Mad Devs, [https://maddevs.io/writeups/pgvector-postgresql-relational-data-ai-embeddings/](https://maddevs.io/writeups/pgvector-postgresql-relational-data-ai-embeddings/)  
30. pgvector, a guide for DBA \- Part 2: Indexes (update march 2026\) \- dbi services, [https://www.dbi-services.com/blog/pgvector-a-guide-for-dba-part-2-indexes-update-march-2026/](https://www.dbi-services.com/blog/pgvector-a-guide-for-dba-part-2-indexes-update-march-2026/)  
31. HNSW indexes | Supabase Docs, [https://supabase.com/docs/guides/ai/vector-indexes/hnsw-indexes](https://supabase.com/docs/guides/ai/vector-indexes/hnsw-indexes)  
32. pgvector Review 2026: Vector Search Inside PostgreSQL \- PE Collective, [https://pecollective.com/tools/pgvector/](https://pecollective.com/tools/pgvector/)  
33. pgvector performance: Benchmark results and 5 ways to boost performance, [https://www.instaclustr.com/education/vector-database/pgvector-performance-benchmark-results-and-5-ways-to-boost-performance/](https://www.instaclustr.com/education/vector-database/pgvector-performance-benchmark-results-and-5-ways-to-boost-performance/)  
34. Supercharging vector search performance and relevance with pgvector 0.8.0 on Amazon Aurora PostgreSQL | AWS Database Blog, [https://aws.amazon.com/blogs/database/supercharging-vector-search-performance-and-relevance-with-pgvector-0-8-0-on-amazon-aurora-postgresql/](https://aws.amazon.com/blogs/database/supercharging-vector-search-performance-and-relevance-with-pgvector-0-8-0-on-amazon-aurora-postgresql/)  
35. HNSW vs IVFFlat: How to Choose the Right Vector Index \- BigData Boutique, [https://bigdataboutique.com/blog/hnsw-vs-ivfflat-how-to-choose-the-right-vector-index](https://bigdataboutique.com/blog/hnsw-vs-ivfflat-how-to-choose-the-right-vector-index)  
36. PGVector: HNSW vs IVFFlat — A Comprehensive Study | by BavalpreetSinghh \- Medium, [https://medium.com/@bavalpreetsinghh/pgvector-hnsw-vs-ivfflat-a-comprehensive-study-21ce0aaab931](https://medium.com/@bavalpreetsinghh/pgvector-hnsw-vs-ivfflat-a-comprehensive-study-21ce0aaab931)  
37. Enable AI-Ready Vector Search with PGVector \- PolarDB \- Alibaba Cloud, [https://www.alibabacloud.com/help/en/polardb/polardb-for-oracle/pgvector-for-oracle](https://www.alibabacloud.com/help/en/polardb/polardb-for-oracle/pgvector-for-oracle)  
38. How to optimize performance when using pgvector \- Azure Cosmos DB for PostgreSQL, [https://learn.microsoft.com/en-us/azure/cosmos-db/postgresql/howto-optimize-performance-pgvector](https://learn.microsoft.com/en-us/azure/cosmos-db/postgresql/howto-optimize-performance-pgvector)  
39. ApsaraDB RDS:Use the pgvector extension to test performance based on IVF indexes \- Alibaba Cloud, [https://www.alibabacloud.com/help/doc-detail/2869991.html](https://www.alibabacloud.com/help/doc-detail/2869991.html)  
40. pgvector Index Selection: IVFFlat vs HNSW for PostgreSQL Vector Search \- Medium, [https://medium.com/@philmcc/pgvector-index-selection-ivfflat-vs-hnsw-for-postgresql-vector-search-6eff26aaa90c](https://medium.com/@philmcc/pgvector-index-selection-ivfflat-vs-hnsw-for-postgresql-vector-search-6eff26aaa90c)  
41. Understanding the Real Challenges of HNSW Nearest Neighbor Search by Re-implementing from the Paper: Deep Dive into pgvector \- Zenn, [https://zenn.dev/jobmore/articles/hnsw-pgvector-deep-dive?locale=en](https://zenn.dev/jobmore/articles/hnsw-pgvector-deep-dive?locale=en)  
42. Hierarchical Navigable Small Worlds (HNSW) \- Pinecone, [https://www.pinecone.io/learn/series/faiss/hnsw/](https://www.pinecone.io/learn/series/faiss/hnsw/)  
43. MySQL Day 48: PGVector HNSW index \- Medium, [https://medium.com/sys-base/mysql-day-48-pgvector-hnsw-index-ab3560a94a04](https://medium.com/sys-base/mysql-day-48-pgvector-hnsw-index-ab3560a94a04)  
44. Running pgvector in production on Amazon Aurora PostgreSQL | AWS Database Blog, [https://aws.amazon.com/blogs/database/running-pgvector-in-production-on-amazon-aurora-postgresql/](https://aws.amazon.com/blogs/database/running-pgvector-in-production-on-amazon-aurora-postgresql/)  
45. Efficient and Robust Approximate Nearest Neighbor Search Using Hierarchical Navigable Small World Graphs \- Khoury College of Computer Sciences, [https://khoury.northeastern.edu/home/pandey/courses/cs7270/fall25/papers/vectordb/HNSW.pdf](https://khoury.northeastern.edu/home/pandey/courses/cs7270/fall25/papers/vectordb/HNSW.pdf)  
46. A cluster-based iterative search approach over HNSW, [https://sol.sbc.org.br/index.php/eramiars/article/download/39410/39182/](https://sol.sbc.org.br/index.php/eramiars/article/download/39410/39182/)  
47. Benchmarking pgvector RAG performance across different dataset sizes \- Mastra, [https://mastra.ai/blog/pgvector-perf](https://mastra.ai/blog/pgvector-perf)  
48. How to calculate amount of RAM required for serving X N-dimensional vectors with pgvector (HNSW)? \- Stack Overflow, [https://stackoverflow.com/questions/77401874/how-to-calculate-amount-of-ram-required-for-serving-x-n-dimensional-vectors-with](https://stackoverflow.com/questions/77401874/how-to-calculate-amount-of-ram-required-for-serving-x-n-dimensional-vectors-with)  
49. Pgvector vs. Qdrant: Open-Source Vector Database Comparison \- Tiger Data, [https://www.tigerdata.com/blog/pgvector-vs-qdrant](https://www.tigerdata.com/blog/pgvector-vs-qdrant)  
50. The AI Engineer's Playbook: Mastering Vector Search & Management (Part 2\) \- Medium, [https://medium.com/data-science-collective/the-ai-engineers-playbook-mastering-vector-search-management-part-2-7a74b8038bc5](https://medium.com/data-science-collective/the-ai-engineers-playbook-mastering-vector-search-management-part-2-7a74b8038bc5)  
51. Best Vector Databases in 2026: A Complete Comparison Guide \- Firecrawl, [https://www.firecrawl.dev/blog/best-vector-databases](https://www.firecrawl.dev/blog/best-vector-databases)  
52. Optimizing Vector Search at Scale: Lessons from pgvector & Supabase Performance Tuning | by Dikhyant Krishna Dalai | Medium, [https://medium.com/@dikhyantkrishnadalai/optimizing-vector-search-at-scale-lessons-from-pgvector-supabase-performance-tuning-ce4ada4ba2ed](https://medium.com/@dikhyantkrishnadalai/optimizing-vector-search-at-scale-lessons-from-pgvector-supabase-performance-tuning-ce4ada4ba2ed)  
53. Qdrant Cloud Pricing 2026: Tiers, Costs And Self-Hosted Crossover \- RankSquire, [https://ranksquire.com/2026/04/19/qdrant-cloud-pricing-2026/](https://ranksquire.com/2026/04/19/qdrant-cloud-pricing-2026/)  
54. pgvector \- Tecnisys Docs, [https://docs.tecnisys.com.br/pgsys-ecosystem/pdf/pgvector/0.8.0/pgvector-0.8.0.pdf](https://docs.tecnisys.com.br/pgsys-ecosystem/pdf/pgvector/0.8.0/pgvector-0.8.0.pdf)  
55. [https://ftp.sun.ac.za/ftp/pub/mirrors/apt.postgresql.org/dists/bookworm-pgdg-testing/main/binary-s390x/Packages](https://ftp.sun.ac.za/ftp/pub/mirrors/apt.postgresql.org/dists/bookworm-pgdg-testing/main/binary-s390x/Packages)  
56. Build a RAG System with pgvector on Managed PostgreSQL (2026) | DanubeData, [https://danubedata.ro/blog/pgvector-rag-managed-postgres-2026](https://danubedata.ro/blog/pgvector-rag-managed-postgres-2026)  
57. Postgres \+ pgvector: Production Retrieval on a Budget | by Velorum \- Medium, [https://medium.com/@1nick1patel1/postgres-pgvector-production-retrieval-on-a-budget-814df87df5c9](https://medium.com/@1nick1patel1/postgres-pgvector-production-retrieval-on-a-budget-814df87df5c9)  
58. A Coding Guide to Implement a pgvector-Powered Semantic, Hybrid, Sparse, and Quantized Vector Search System \- MarkTechPost, [https://www.marktechpost.com/2026/05/28/a-coding-guide-to-implement-a-pgvector-powered-semantic-hybrid-sparse-and-quantized-vector-search-system/](https://www.marktechpost.com/2026/05/28/a-coding-guide-to-implement-a-pgvector-powered-semantic-hybrid-sparse-and-quantized-vector-search-system/)  
59. Enable pgvector and Load Embeddings | DigitalOcean Documentation, [https://docs.digitalocean.com/products/vector-databases/postgresql/how-to/load-embeddings/](https://docs.digitalocean.com/products/vector-databases/postgresql/how-to/load-embeddings/)  
60. Understanding Semantic and Hybrid Search with Python and pgvector | by Hasan Sajedi, [https://hasansajedi.medium.com/understanding-semantic-and-hybrid-search-with-python-and-pgvector-0967e83803e6](https://hasansajedi.medium.com/understanding-semantic-and-hybrid-search-with-python-and-pgvector-0967e83803e6)  
61. pgvector Benchmarks, Per Tier: Honest, Reproducible Numbers from Solo to Scale, [https://rivestack.io/blog/pgvector-performance-nvme-vs-cloud-ssd-benchmarks](https://rivestack.io/blog/pgvector-performance-nvme-vs-cloud-ssd-benchmarks)  
62. Is Actian VectorAI DB the Best Embedded pgvector Alternative?, [https://www.actian.com/blog/developer/is-actian-vectorai-db-the-best-embedded-pgvector-alternative/](https://www.actian.com/blog/developer/is-actian-vectorai-db-the-best-embedded-pgvector-alternative/)  
63. pgvector vs pgvectorscale: When Vanilla Isn't Enough \- Rivestack, [https://rivestack.io/blog/pgvector-vs-pgvectorscale](https://rivestack.io/blog/pgvector-vs-pgvectorscale)  
64. Advanced Vector Workloads with pgvectorscale and Hybrid Search \- DigitalOcean Docs, [https://docs.digitalocean.com/products/vector-databases/postgresql/how-to/advanced-workloads/](https://docs.digitalocean.com/products/vector-databases/postgresql/how-to/advanced-workloads/)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGcAAAAbCAYAAABhoZFDAAADKElEQVR4Xu2YWahNURjHP0PIPIRISUmUeCDyYEjJAymeRCQZEkKZMz6IZB4iVyiJPKCIDFGkZCgeJJEXRSSKIiT+/75vdfZZ1zlnr3vPPnc/rF/92vuub5179j5rrW99e4tEIpEihsEncJ4fiOSDO3CQ3xjCEngfPoZ9vFg1OA4/mX/hH3jLYv3gN2v/Yd6D7SzeFIyAZ+BNuBE+N4+JXhuvkdc/1n2gBG3gG78xlDg4xeRmcMaIftl6+AUOKQ5XjQ7mV9EbTHIIHpRCnzzQDB6w8zrTsQWOh1ftmKST6MDuFp2Up4vDYRwVnSGtYG8vlgW8Sa6SwfY3Z9+RQjhXcNK4ozsnfeEi2B5eTLSTE3CFne+ACxOxYF7BzX5jhowWHZy9oquUs6xFUY/qMwP29BtTUGpwOCjuN9tjR05uypTttgamvoF2npp98K7JH+qh6OoZl+hTigFwnTQu/byEH+F12NGLZcFEadgM3m9Hf3CYYZbDlnC1tfUwOdkJJ8Nb0d/LZYnUjDI5OCGlHnMoPzPNDwTAWcf/Uav6nyvzGuzsByrASUz8wZkLF8NZUr9wuSC6ms7CB3ArbF7UIwXzzV8SllaGwjWwrR9ICWfbJdHB4bFWDIfnYRc/UAamXsLrpCfhYdFVP0m0aMgEji595gcygjdCufK46q7An7BbslMKuE9RpuFQn8L3Ur/CKoXbT9zKYYbZJpr+z1ksE26Y3JBrwS5zjv09XXT1LHUdMobZgaXtBD9Qhv+ltbWir2W2w5nWVnXi4FSmyQaHeZPy4TOU0AprpWh1Qx18ev4MX0gDNswGwAfKqX5jBfy0RjjIdbC16D7EZ56qwjKPs5ZO9mKVYBn9AY70AyVgCfvIbzT4AMxrmOIHqkwv0c08FK504ldrXDmrYHfRtwRdE7FGww3RDQ5r8xBYBn8XvcBysNJ5J/odrAhnmw7e+G+Lsx83bK7I0FWZBlaXrDLTwns7JfoQyXdrfO1PuZI40GQD3AQvi04+ZgLaaJZJ4QsjOWGB6OzlEueGRiM5gBsY3/vsFH393d+M5ITb8LXoph6JRCKRSCQSiUQq8g/yqsU9up2c/QAAAABJRU5ErkJggg==>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADgAAAAbCAYAAAApvkyGAAABzUlEQVR4Xu2WTShEURTHD5KvYoWUr5JssESIhQVlY+lrMQthYS9LG0lRiqKokaREURbCVkk2WFDKwsLCQthR4n+65/Xuu81482aGmun+6lfzznlvevee+869RBaLJU4m4AP81ryCtZK/0eKXsEVMGdJ+gA6n8EMs1OID8ARWa7GUJERupcYlVgL3Yb5c/yvDcAMeijzLjqXafbFSAF9EXopFpAYX6L+y4Dy8gOdiJ1yDO7DHvTUqmXAFjsAcI5co6yJX8Qw2etP+zMIO+b0gvsF6uEdq9v2YgnVmMEl0iTzAsDflDy+BsHbNFWOP5Zqr2O6mo8Iz/FdMi+/wGWZ708G4EyfNxC+Uw3vyfm+RrHQeCMAouauKVwlXsddzRwBqyO1YsVTNoQwumsEk0AdXYYZYQerdtvWbgpCWA+S9ZIlUgxiDn2Ku5Pnj5tbvxy7MM4MJ0Aa3SHV4nSP4BauMeFT6SZ0Smkm14CeRZ4wHeUBq7/GjidQ2wc8lSit8hMVmAgyRqiJ3/pjg5cVbwTWp8x+/JMtHpDkKMFOgm9SSajATMRKCt+R+JsueLNEgfJUcF4UbF1f6X+EWzgeDGXGT1JYT70nGYrFYLBaLJTI/vv1yYLgwa/AAAAAASUVORK5CYII=>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAsAAAAdCAYAAAB8I5agAAAAv0lEQVR4XmNgGF4gFYg/Q/F3IGZGlcYEbVB8CF0CG9gPxZPRJdABJwPEehCOR5NjiIHi20B8BIgnAfF/KFZAKIMAohU7AvF7KFaGih0H4ntQjAJAJvVDMQysAuLFUAwHpgwQq1yhGAZAJmZDMRxkAPFfIOaCYhCQZIAYYAjFcECS4jwgvowsAAR+QPyBARLFINwMkzAB4gcwDhCIAvFNID4BxHpQXIQkz1ANxHugGJQOnIH4ORDPgmKY80bByAEArKcxNQ1SxSIAAAAASUVORK5CYII=>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAB8AAAAZCAYAAADJ9/UkAAAB3klEQVR4Xu2UP0hcQRCHJypKMCiiiWIEIVgEBDFRjP9AsbDUQrBLkUggINhYiZImRUQsJCBitLERQVQEC0UTUUSMgYAgpAnWSooQRQQb/f2YWd337p13kOIK74MPbmf37eybm7ciaRKTC1+YGaG5/yIHjsA18xcch4+9NY3wyvwLv8JNWxcFD7kI1+G86F7+fjekNDk3qPHGL+E53PBizfDCvBRN3uvN+9TDfVgOs+F3OGQGKBJ9m7FQfNLiPAhpgp/Mu2AVWbk3Ns6Df2C/GaBQdPJLKP5ONPlrG/NtkkneLfpcQXgiHiUS28GDopu02ZjJF8xZuAd/wOc275iCp7BHbvtnILAiCXbgljeuhQcmPzvCTQ9hllsEVkX7wvVDsWiDdpoJ6YInsMKLZcKnpqNKtDostYMHZizfi7Fxt824MBk9gq9Cc1GUiiYa9WL8W/imPkvwzIxLypKzO3fNVovxINX2exmumI4y0eTDXuyjRCd3d0QM/D95G1Wajvew3X6zsXixUEedaPIOL9ZisUdejM+wEWkMn0Wb4oPJ8Rz8DZ/Zmj6J7dhpCVaCPBD9xNz9wKb8BxvMACwtTxoly8SqOCbMb/Cn6Df90Jt3PIEzonf/MXwbnE6TJs194Rrlpn/74D8cBAAAAABJRU5ErkJggg==>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADMAAAAZCAYAAACclhZ6AAACpUlEQVR4Xu2WS8gOcRTGH7nkrlxL5IvYuO5cir5YyG2hJBvXZOETS2TtuiChhEgsrCT33BdyiVwi98uCkpSSEBLP850z35wZM++7+4rmqV/NnP+ZmfO875nzH6BSpVZXo/OAdMyspJrlnCMXyB7SPqy3cw6Re+Q2WRbWo1aTh+QG2Uo6ZJebNZXcJ1fJMdI/u1yuRuefNrObXCFnnd8oNrMUaU43MoC8JnNCzi5nJ2lLOpPzZHnImedcI91JG7KJHAk50lDylgzz8+nkMeyaulrlFJkZQn6QEY40hvyEPURqIL+ckR6TFpB3fqzCHzlNLRnAINhz43X6kfMGnyJ7XalqmdkGK6CWVsCuFT1DfIrHVOiokDM75Kg1FYuFvoe1X9Ql/G2wULXMPIHdaINzEfZuqV0SbUZaaLx+vMdmkhkhR+9D1FeyhXR1lLM+kwGcJNdzsUKtdPLFqDW+OypMSONgrTfaz3eg2MxYj6nd5oacvJnPZC/p5xSZOQ5rtboq+2c0ZRTTP5HXB7Lfj9USRWZkWrH5sNYqM/MFNh3VoqLIzAlYl9RVNNMpt6aiNcXyeg4bv9I6pIVqiiWa4LFpZFLI0XnUN7IR1glCg0TnUadgY7qu/lszsRhJG+SZXEx6Qe74sfabpNA+LRnpNGsgvUNO3J+08Sq2MMTuku3hXNIQ2peLFaqWmTVIi476iPSBsdC4XyyGmU6kIkUcw4ORGk6k++bHsO4TDZcqmumSW+tFXiG7aepl/kQGJkmwYSA0YiXtHxqna1sygEXOZaTtrBbNt7Gm5DPYhiqpRd/AfrRSLYF9cqhYITM3PdY35MnEUUefIi/J5LAuJd9m2osOw+6j/UfvQF567kGYKY3cHtnlZk0kB8hpcosMzy5XqlSpUqVKraM/0RrRp9PfOCgAAAAASUVORK5CYII=>

[image6]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAALMAAAAbCAYAAAA3W75wAAAElElEQVR4Xu2ba4hVVRTHl2mlaWQIKiU1PRQf+ChFJKUmhwoz/CJioc6MYn0RFSLIByIKWjooQRRR+UF6QGSEGoIICqYS+PioYOCAgqj5wQcFCmLrz1rbu2fN2d57555z554z+wd/vHvt673nrLX23mvvc4coEolEIpFI32Ye6whrA+tX1j/6ejvrpKqwfEZys3NsR6ShQdIibpuNHUn7uL7eyvrW60MbKiwxmfNJTOYEfrGGSK6w8VvqvUa5schrv68qLNYZkXwRit9A1h3WSNtRZELOiOSDUPzeZnVaY9EJOSOSD0Lx28TaZY210sq6r7pr+m55fR+ZvnphnbFStY9k89Bf7f1Yf7He1XYatLD2sPayRqkcHSSb06LhfJuWf238HKiXl1ljrYwgCUpSMr/HuqR9jZDMM1nbVE0k1/WK9k3R9uvarpXBrIMkQfybtVoFHiE5H12v7aLg/NukSsO/Npk/IDnluM36jtXWtbt2plFyMoMTVFkyP0tykZXqE/lvZfGdgdnwORUS61/WE9q3gmRDMUjbtYKBvJgkmLj/ZhWYqLbZ2i4Kzr9u4KbhX5vMmfMqhZP5T6osmbMi5IzjJCWA4weSpcuCmbWZJEg94XPWVdYAFfiQdY9KgQaYYTayflO94/XlDfi2Uv86hpLECk/1fELxy4yYzGFiMgsh/zoaJpldPZSUzMeosZL5aRWuqd2zX6SuT49eVmHHfIE1y+urBvxWwO66d5MMcgfKNCQ4gC+ha1T9ktwION+W828Sa1kfG5uNX+ZMpnAyn6XKkvkZ6l4XP0y48UqwzpihwjW9oLYmbc8leYJkNylIPGsDj5FsgKEQqBvbje08yUYJ3/8pawnJoAeYoSBczwS1OZ43bQs2lkOs0fCUNSRQ7j3DSe49Cefbavzr+INklfex8cscbN5wsVg6n1SBNrVDX7FGq72eWGe8pMI1jVEbnve7NnbIj6rdEUrmQ6zLqlASYVZf7rURUHwXbNgkYRbG06zx2v+WCgnvJwwGMPw73bNZcBx2jsLXMpV1heSzQmwhuZ9JtoMZpsJn/G76HM635fyL8g2nYNA3+i98hQHpY+NXF9axbrCuq06TXMgBKt3czgfvrh8hZ2B3jZkAZ6ELWN+zTpGcQFhCyYyjN6xGUIvpc8COwP+kWkPy3VixUE/7IMiHVeNMH47x8D14WBACg6uT5FgwCQyc/6j7j3d8drBussbaDiolM5Idn+N+8GPB/ZXzLyY6nL9DAAPYr7Edofj1SdJwBpL5DWtUXOCSkr0aMCN9zXpTlQSO9BrlbPpn6r6CVQMGXqsK4L5WlbofkEb8CkMazkAyhxLMzbihGrIS+rO+JElWB2Yw/4khwOboNWPrDbAxxelELZwhKTshnPIcJTmTn++/idKJX2HoqTPc42fUlzhZ+JG6/7wQ9S+W/Yct/ZWwkEqlmBNKNh/sS/YbW2/RQbU/8MF+AQMCQikKfcF60X8T9Tx+hSRLZ2DnjroxVDumCU57sLlqBGotqaohy/jljiydEZM5e7KMX+6IfzaVT0J/NhWJRCKRSCSSN/4HXKshj/fgnBMAAAAASUVORK5CYII=>

[image7]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA0AAAAaCAYAAABsONZfAAAAeElEQVR4XmNgGAXDGmQC8X8kvBsq7ockdgmK4YAsTdJAPANJAUyTMBC3Q8UwNIGAPwOmJhCwhIph1eTNgF2TGVSMepo8GLBrcoWKUU+TOQNC0wmoGCcQb4WKvYBie6gcHEyH4u9AfA2IbwNxFQPCMBB+B1c9CugJADJxQ0C+97WJAAAAAElFTkSuQmCC>

[image8]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA0AAAAaCAYAAABsONZfAAAAh0lEQVR4XmNgGAXDGkwE4v9ouBgqtxFN3BkqTp4mEHBHkrgJxIxQcQ0gfg7ELFCMApiB+BYUgzQ6QMX7GSAuwQlyoBikaR4QcwHxGyA2QFaEDoSh+DcQfwXifCA+jKICD9jNALHtGxDnosnhBGRpSmKAaPoOxKJocjgBOxBfB+I+dIlRMGAAAEG6KyV6/9BKAAAAAElFTkSuQmCC>

[image9]: <data:image/png;base64,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>

[image10]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFAAAAAZCAYAAACmRqkJAAACKklEQVR4Xu2YO0tcURSFN0YxVhJfiaWI4D8QJaW/wVIljZ3pIiJpREQREQsxRUjhWxslhQRMlcIkvkhhIYK/wMKfEPfmnHH2rNl6L2fOMFe5HyyYvc7MYs5i7muIcnJyXggDxlwHXgg6N1ZmJskLrJBvMM+xWsALQefGyqwmr1jDrCNcSGId5gVWG3gh6NxYmdXgwuuA9Y/1u3Q5mU2YF1nt4IWgc2NlVptt1l80k9iCOdZmdW6szGoTVOAOzLjZG9Z/pXHvzyjvl/c0Ohczs0pQgbsw42YHWVdUXmA3a8N7VoE6FzOzihT4B80k9mCWzb4F75DKCxQ+eM8qUOdamV2sT+S+9DKrvnTZZJL1OaWmyGWmyS0Q9AvMCywSVKB1CL8D7zvZBY54zyoQD2HMXGU1+Nc/WGNqrVZIgSdoJmFdRHCzco9kFTjqPatAvIhg5jW586vwhVyhtUYKPEUzCfmQxjrc9sku8KP3rAJ1rpXZy3rtX5+zhtSahTwKTlD5ofqUGr3SElRgmhvpr1QsUM4tghRSuDrfsN57v0DaG2k5DcyjWSOkwDM0k7AKxMeuHnInV5EUdkyuvGk/i24f3u3AAjFT6CP3zFzLPxqWvOQZ+I7cXn5S+bXhUawCW8ELAQvEzH7WrJrlivwssQp8A14IWCBmXlLx1yuSW6JnyRrM8s9JM3gh6NxYmZkkL7BCVmCW81ITeCHo3FiZmaQD5k6YQ9G5sTJzXgr3WBqf/FB6kXIAAAAASUVORK5CYII=>

[image11]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAmwAAABMCAYAAADQpus6AAADZElEQVR4Xu3dO4icVRQH8OMbDGowaYJNfKQQX8TCkEASiOILQRtBxQcqYiXBiIiBEGxMClOkCfYhEDBiEiWNjYUKdoKPQhIttLITKxXRc7nfst/c3Z2ZLJlH2N8P/szde4bZKQ/3zv1uBAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAFzW1mc+aicBAJgvn7UTAADMh0OZw5kLbQEAgNl7MXM2sydzqqkBADAHvs1syXyR2TpYAgBgHuzNHM+cyxxtagAAAAAAAAAAAAAAwBpwMPNf5o/M50NyvntfPwAATMHGWGzAHmxqrXWZbVGbOw0bAMAUvROLTdsVTW2Y99oJAAAmozRpn0Zt2N5uasN8kLmqnQQAYDI2ZH7N/JV5oKkBADBHHCgAANacn6I2QPsz+7rxbwPvGK49lXlT8/el9mXUz36tLYyhXBT/SZcFh3vjvqcyH0bdjj0drr8CAGasNEDvduNHom49Luf+dqJTmp5+g/Zkb9y3PXNghTzde98oT0T9f9+3hRGei3pR/MJ3vSdqE7fgtu71UOaOzJ+ZGzJ3Rb2ztChbswAAU9dv2B6K5Ru2F2LlVbNbM/9m7s7szlw9WJ6I1a7ileby9278aub6Xq11qnu9PZw4BQBmrN+wPRPLN2yjlFWvciDg77bQM2yFrax+XYwfMg+3k2Mo3++lbvxjZnPUk6flGW9nuvliV2ZLN/64ey2rbj93YwCAqSoNW1l5Wp/5JupWYFlpuxhXRv2c/u/DJuWazMvt5Jh+ybyeeSzq930j6lbvsRjcyi2rhju78cK26bOZI90YAIAVvJk53k5eAl9nnm8nG2czr7STAAAMKveGlhU2AADmUPkN3I3t5BDlN2llqxYAgAm7JfNd5t62sIJyYfyJzH1tAQCAyfgqRh+CuDPzaOatzD+xukd+AACwCjti6SNAxg0AAAAAAADAZaQ8g22Um9sJAADmSzl4AADAlK3LvB/1obmjaNgAAGbg8Vi8eP3aWHoatH8iVMMGADAj56Je0n5dLG3WNGwAAHNgnIvXy+XtJ6M2cJuaGgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAMAa9z9hkIeROgBYSgAAAABJRU5ErkJggg==>

[image12]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADkAAAAZCAYAAACLtIazAAABMklEQVR4Xu2UMUoDURCGR4tgZStil140EcQL2OQEsbBV72DhBRK1UMRGi9wghY0KYqE30Eq9gKAomkJC/If3R997MRtJ9hWB+eAr9p/ZSWb3sSKGYRiGYRgjUIQdzxXmZ1F+xHxYahLOU5usVb3slubKFFyDXxIuuQyvmamHzEdhnuq8Npzzahdww7tOwruESyr7zAYtOUNn40IfLsXN3Ob1EvyE0z8diRiLJXfg+T9d5z0+r9K75C4z9cDLY+7oA5yIan+xKm6m9k/CU3gcdCTiRbKXzHqTezSrJ+ZJ3NxN2IKLYTkNz9K75AmzQUsOQ13c3A9J8DXthx43/VE9SkoJvjFT9etXZi0PFuR39lZUS0YFPoo7Ojfinq6+ve4fUa+6zTnRgPewEBcMwzAMIye+AY/9ZQmazyonAAAAAElFTkSuQmCC>

[image13]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAoAAAAfCAYAAADeKVyVAAAAwElEQVR4XmNgGFRAG4h3A/E5KJZAlWZgEIPiM0AsCcSZUNyFrAgEJkFxBZRvD8UgU+FADYi/Q7EoVMwTil/CFIEA0Qq7gXgXFMNAGhQ/RxJjuAjE1VAMA71QfBgmIAXE//HgeSQrjIAKCEMxCHAA8TcoToKKMeQD8QMYBwqcgPg3FMM0M+QB8R4YBwqagHgZFMMB0QpBbtyExGcC4ptAbADFcACKlZNIfJDj5yPxUcA0BkjSAuF+IGZHlR4FIwkAAAC7OiSznP2AAAAAAElFTkSuQmCC>

[image14]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAmwAAABQCAYAAACksinaAAANs0lEQVR4Xu3dCbC95RzA8Qch2cm+VIoSaWRXEmXNvoyl5MZIlBKyZQmDYspaFOmvSLJmKYRpGQ1DEyKS0pQWMlkaa9PwfD3v8z/Pee573nvOve+pc+7/+5n5zXnf533P/d977v//P7/zLL8nBEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSVoObxbiqbpQkSdLs2DbGV+pGSZIk9e+UMeJza+8O4VcxHhHj1BjbFO2SJEmakmtjnFg3NnaO8b4Y/42xfdN2YfP4+xg3aI4lSZI0RSRd347xt/pCYb0Yp8XYIMbpMT4S44wYe5Y3SZIkaXruHOOyGLetLxQ2iXGLulGSJM2/T4Q0nPad5pxjYsu1d3R7ehg855oYty7O71bcp5V7fIwT6sYpuHGMD8bYqznfOMbv1l4ddmiMHzXHO8bYorgmSZJ6tH+MbzXH64eUbN13cHmtzUMqFdGG53y3OT63vKBenRXj33Vjz45vHlnMkM/zcelWIQ3F0vOXPbI4liRJPXpNjJObY3pXSL7aekr+E+PYurFxdUjP2yHGRUNX1CeGPf9YN07BbWLs0xxfHOOdxbVHFcdPCun3nt20ebxlSMmcJEnqyb5h0MN2lzC6h63Lk0N6Hkkd8600HbvEeGPdOAVvKo4Z6iYBI5mvMZR+dHP87PKCJEnq1/Nj/LA5/lhIidcrY9xh7R1Lu2FIPWtfqNrVr4/XDSO8tm5o0bWA4SXNI71kzF/Lydqrw3Ax3k+FtIKVJJ1jMK/xqLV3SNI67AUh1V6aliPqhlXs1JCSjRJFSH9ZnH8zpCEi6fpCz2fbPLKMHrAfhMGQ5DieUDeMgYUk/DlL+WndIEmzhv9U/xLjzOaYOD/Gc8ubVohK5kwOnxY+ebcNf6zUg0NacTYrqG+1VdXGpPqdQnp9N2raeGPLwz59ogQDqzQ1PQeE+X+NbxTjSyHNXxuF2mtrmmPmm+UFIF2Wk7C9Ocar6sYKc9xYzXrH+oIkzZpLq3N6cM6p2paLT9Ab141TcHbd0IOF0P2mc12rq8czb4v5OtnBxfEhMT5UnPfFoaPp4sPSvL/GuUxKV1we4ybN/fTAH9Qcd1lOwiZJqwZv+vwHWmNuUB+rph5TN0wJP8Pt68YVWgizk7DRg/jPqu3wMJxYv7c4ZrL3T4rzvsx7MjHrVkPCdvMYG8a4R4wHxHhYjIfH2LppY65hOazPAhKukcC9tSVY2QkTNknrtFeE9oTtyJDmoazUfsUxQ3b5E/ajm7Z83iXfw/BGeV76Rxhevt+HhdBvwkYSxRsyPWV7NG0M59I7yCT6crXi60Oa95fn3zwoLP6ZrwiDXrV7hfT9ZrxJsqdj3+Y9mZh1qyFhm9RJYbBoYJRdQ6qvRgLnql5J6ySGJnLhyYwCk2WxS+Z20HvDsAV7/k3ySXdN3RBS4pGTq3c3511Iav4a47HNOcU4a8zBy5XOS0w6rj+x53hdcV+bhdBfwsYb8aebY+bG7R5SuQMSzYzXnO+J7/k5TVt+5A3t181xVvYqsuKtnMfHfLO213XbsPh1KGOpUgd9JhNPjfHJOY++9Z2w1d+vMVsxzupYSfo/3tT3rtpe2LRnDLs9rTlmQjFvKuNqm0DN196uOWbCcVtiUeO+45pjegVrbBzd939+CyH1XLWh/ZQRQdmAGj/jgVXbl2NcWJxfFeOY5pj7qRGWh4N2C4sr8l/QPLIYgcS7xGKEcV7XSeVSCG3q1yHHR8ubCk9cBdE3/m2Neo3fHha/tjlyj22t/n6N2QtJGsufw+IyESQOzD0BNYry5ODsns0jewWyhx/JFF4aUoK2aXOOsqBlVvawHdacZ/lrt+E+KtS3YeHE4+rGkIZ1616kMroshOGfZSW+H1KCljHESYJZ9rDx8x0QhvfF5A2cnqhtw/ACA+R9Gvmk/o3yQkhfo74fjwiLX4Mydh3c2uroukG94vd9fb3GfBjj3/osx6SrwWf9Z+L7k6SxfL04Zij0PWE4YWAItM2OYVB0NG+m/NuQ5l7dpzkHyUaNxOQpzTEJI+cPac6vDWnroTbcN6rXiPa+a48txNisblym7WNcGVKFfTYcZ94Ow5bnFff8rLlGspxLDFwc0hAp7bw2pTObxwti3LW8ED0jTKe21Jq6oQfPbB63iXG/8kIHejhZ0MIqZArpdsnzo7hv0jd8LOc5y0XCtqZuvI4shFSAeJaD3v9JvDgs/hqzFA8NktQTuuxJFnDvGG9rjn8c0psr/yHSu0Pix0bKTJLnk2OJauOToBDspJaatLwa0IM5DoZIfxPSirx5wFAfmK9HojkO5jO+LKQVh4dW12rHNY+UOemqlj/Kcp4zj3auG+YcHxafVTdK0mp2bIx3hTRcRzIAEjmGQt8RUk8Rq0GZRN/WQ1JW4V8Kqxsn3XuQnsFJKqbPKxLhcVbI8btht4N5wd8hTJKw0cO7RxgvYcsfAEzYuk2ytdc8+F6MO9WNkqRuS72pZszVmgRFN+lpWVeQ1NCr2SUPL8+LnLCxu0buEWEuJMPcbNbNz5OHw7dsrpOwvTykoeMPNG2jHN88fjgMVtXmr0c8KqRhfY7bhtz6ru83i/LvYCVOCGmHg1nBNISVYl5nPcdXkqR1UlvCRk8tCRRFVdl3kuSMcwo9g4RtzzBewvb55rFM2PCZMNicnKTwD8W10rqQsOWkdiUo0bNUqZzr0vp1wzJMUsJIkqRVrRwSzXXnQIJ2cnPMxH/Ot2jOSdiYtM0wXrkFF72PXwxpBXOWF8dwXz3sx9ekTAwro3PvXS0/hxXM+4eU5K2mIXgKUrdNZRgXC5WOiHFR6L83it8ncxzL3+c4XlQ3TIgPD9Se7HvhDnMv3xBj3/qCJEmzruxhI7Lcwwbm79U9bCRs9LDRcwYKEtMTR8mUsrcsJ2zcV2/wzdf8Reie85efc1hI3wflWWapJ2mlSLbyriasUK5rvI2KLJeU6Xs4NP8+we9z3B4zemQPLM4pnVF/722RSxCxyv2SkP68PzVtfSDJzzUJrwjzN3VBkrSOKxO2uoctJ2wkFHXCRs8YyVTuYaNXhVXKtwvp3oy5VSBhq3vY2F2Ce8s/t5afw04TrKRkPuZnB5fnHonvBsU5CRgrvmvcw0KP08Pw67vQPO5TtPUh/z7BnzeqB7TGava6iDbPb0uy+fv0vJAWVtHLyj6o9OgdFdLcxpzs94FV2+zYwsIh9vllSF+SpLlRJmy5JhtIitjt4fyQJn/zpktwT7nooF7QQpHiPHSKctEByVyJN+yyeHGb+jmHV+fzjEQ4F8ku8TrnrdRGyT1SJDsMXVNEe5PB5d4wHF7+PpdCLUj+fpRYLXppSL1vo5BQnRjSwic+KLC6uI+5fW2Wqh0oSdLMKRO2Scp6tCVsDH/tUJyjTNiWU6KjfA6FTq/LQrrTxtw1epVqB4bhXrQ2W9UNU8DvMy8MGRcJdVsRbf7OML+xS1vy2rc8zCtJ0lzJxZjZeH7c4q3sckA5lw1jHNy0MbSVe+HYQSNjNSjoAaJm4KTyc34eBl9/3iaNbx3SjhklFgjwmozC0OLZoT2h6xN771LfMb+mV4a0EGLU7zNbLyzuSQN1CEdhEcHf68YpoHeSPWEZUmWuGj8Du5Hkn4d44Nq7JUmaA3lojX1rxy2jwLDV7iH1pFBOosuRzeMhYfyJ66XlPGeWkJix8wXbwZEYZfQcLjXsSWKxVK/USjFXjYRyh+acPzMfj8I8MJLJXBQ5Wyq5ZAj8byEV254WvjZz4C4Lg/2K8zxKSZKkVuzRStLFBP6yh5GixOW+v202CoM9a6eJSfjZGcXxKKwgZTu6y6v2rh7DjGFWeg+n7aLmkZXFxxTtkiRJi9CrRnFhkptybtfRzbUuXwtp2HnarimODwrDixe+WhyXmH9XD28eUJ23yT2u08brC4b68yIDFj2c0xxLkiQNIQFi+63TirauBRgkcmvqxsr9i+NNi+M2zOe6sG4sUFCWVcHsI3xujPcPX25FTxlz3fIK0l1D2ou4S17gMkr5M3Uls8yfozcvD+e3YXXzWSGtPpUkSVoSK1spkHt1c755ca0NC0GoudaF5GoS1G+bBPPNSNy6hhN3CoPeKxK2emFFiaSwC8kaRZEnMU6PXsYcTea27VVfkCRJynYLg5pze5cXWizVw8UKztyrNm4SMmnCxhw1kqyuJIo5eCSi4HsYtUDk7iEN73ahTht/Zk4UxzFJwsYimbfH2K++IEmSlDF/im24Hh1jl+paxnw1FgCU5SdGRUapjK7h1WzShI0Vn+eF9ppqGT2HlAFhccTGw5eG1N97W5Rba41bHPktdUMHdk5gtSgrnCVJkkZi83p6mqhhNwp7XlI2g3lv7Mu6XUirMpnkz84IJFDck+UkhOFJyljUkbe9mjRhozwGK1sp+9HlkpAWEnQVNCZZpcgy892of7Z9SEWQNwtpGJXdLPKctZwo0rvHatL658mlOpBrCI6D15EFFJRXkSRJ6kSJj6Xqlc0T6uv9q26UJEmaZ5MuFph1TOY/qW6UJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmStBz/A94rB2DCrf0GAAAAAElFTkSuQmCC>

[image15]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACQAAAAWCAYAAACosj4+AAABnUlEQVR4Xu2WzStEURjGXx9J+SzFxo6sfC2EDcVCYSM7pchSCYkUSsrHhqSkWEhkqRRbZS3Jykopf4IoC/G8zvuad65pzr0TNSO/+i3uczv3PGfmzD1D9E+GkguP4IJYFX/71+kjN++8BmlXKA8eft2OUQyP4Y64BgvFKFTAA3gBb+EyLBCVbHJzfZKoUBa8hJMm24LbYlj42SewXK5b4BO5gqziLdQG32GNybrhs5hv8mT0wnvYabI9cs9mqyXzFpomN6DUZE2SsV0mT0YHfINDJlun2HPaJfMW2iA3wO6XRsnYEZNH5Ybc18aWSOYttEnfC9VKxo6bPAoD5MaPikrmFVokN7DIZA2SscMmD0slfKTEY72FxshNrD9XplkytsfkYeC9cg37gzcEbyH9NOpMxm/UF7HM5D5y4DkcNNmsyItkvIUYfl/Mmet9uCIqPMkdrDdZkF14RrGjib0SdY+GKsQrW4Kr8JTcm5oHsgqv8hXOmMyimzjog6iEKhSWVjgRDCPytwvxYatnUqr8WCE+TqaCYQrEFUqbP2gfjcp0pIJehOYAAAAASUVORK5CYII=>

[image16]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAC8AAAAVCAYAAADWxrdnAAACO0lEQVR4Xu2XTUhWQRiFX1MLM6MoChHEECz6IcFoVQSB4EqLaBVU2s7AFrYxtCAQRKzcSEWRQha0CENsExhCi3ZBi4SCUFqGG1dREnaO74y+d5wrV8M+Ew88cOfMfDPnzt9VkQ1taMXKA89AB6hyrEWdBrtCMx88D01oOxgE90Ef6HZerrQXvAHF1lx34bmVxkCr8Rj+iSnnQtw6w9aIhT8JZsFB4/GHP0GJI1caAo2+EAt/XTT8buMddt5Zx3LFw1YDNocVRtyWx0FRWGFUDz76Qiz8HdGgO4x3wHlXHVm1BXSBD+A3mAbtzvfiiz0Cn0AveAqumXqrbWDGF2Lh78ni8JXOa3NkFQ/8Gfe8H7wW7eetLGzBUdDk2njdAOcDz2vSP8TC3xQdYKfxODC9ZkcWcUYZ3orjcZbZ17ijM9FCxe0V5vLiKs4pFp7bgp2XGu+o8zgbaTMSqhq0hCa0CbwU7Y9cSlbPK+12e+cfYuEPiXbKwb3qRPcsX8i+1FLaA+6GpuiKfgGfHdzDDYkWIltFv/wxcbXmFAtPPQC3TJnLHwY5ItrRxcC34uztM2Xu8TFwQfQqJlPgl+i+56qUgRHRmyWm7/4hLTz926I3xSvRlylItBA5ITprHChNDPsQ9ItOxntQm2ghUgFeiK72V/ANXDb1VuXghy+sy/BZlfX3PEenRO/pNPEsHJOlP2S8/x/7QtbB08Sb50porpK48hNi/mz/m/CFYED0kP0L8cNF5vW//DNyDvT4wh+40nn2nxWs8wAAAABJRU5ErkJggg==>

[image17]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEkAAAAVCAYAAAAKP8NQAAACwElEQVR4Xu2XWahOURTHl3keMifp4oFbHmTIizKEJEXygJTivpGSboaSUoqMSWS6RBKS4cGQh5vijYQMdZG8eFHyoijx/5+192eddb/7DTpfV33nV786Z63vnLPP3vusvT+RnJycTmRocL5P1BHj4DQfjPSBd4KjXa6e6ApvwUafIHknKSU76TpcGKx3RsEncLANLoG3bSBHtsCTNvAYLrOBjBkOp8KePmEYBGfA3j5RJX1F7zPAJwy94HQ4xCcMXMB+xZNh8LeUvuBfYWP2w2eiz/gGt0m6s0bAc/A5PAQvwyaTr4b18AX8Ivq803CkyXeDO+EH2ALPwgOwu/mN5Wk8WAw/m0SWcLouDceT4F3Rxt8THWnaCleF30T2wEUuVo41oi9MOPAHRZ/1CY4NchAYt52yAO4155ZL8WAtfGUSlv6iPV+JnCFcGQgbSU+F8whHkiPIxr8N8loPV9qLPliGq6L3t3BG8lmvgw/S6QLXfCBwNB6sEzOtMmJKcKNPiL4Il1g2nq5MpwvwU6iGMz4Q2Cp/n3XC5SKcYQODln3xgAWb32iWsM5QTm0Pi/h72Bb8Ke0/LTb2vIuVo9jM6yK673sTZEftTv1CueEDAda0hFmiBbUWcDY0mHOuYI/gCtHVhX6FP+Bq0ZdqEP0s5uklCaxdD+FhE/NsgMtd7LjoNdzv0JeiHcUZwkWF5YT5XfECB/eOCWzAd9H/LFnDe7N4sw6xIdxqzE39QmSCaGPYeM4sFlpfyDmzuLiUG8zt8KZonbsPN6XTyX1Y3Dl7uQJ+FF0kODjFeBcP8k6qoJPIBdhsAxkzGc6G/XzCwH0aP78ePmG4Ih2/UGQMnCOl/39WsuFkW1Kr/kTRUeT+oaONVWfDme63FLWEE4eb0xQ74Obg/8gRqc2/gmKwJPCz9fuuhGPBmT5RR4wX7aCkNPwBUrOPcWeUoLgAAAAASUVORK5CYII=>

[image18]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAmwAAAAxCAYAAABnGvUlAAAFXklEQVR4Xu3cV4hkRRTG8WPOAdODIqioYI6gosKioGBAzGFRDAgiBhTMillBzArmHDDnnMWMGQwYcB8MiIqKgoI+6Pn2VNnVZ3t6euzZHl3+Pzh0Vd07Nz7MocI1AwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABgYAt4LJobR+DA3AAAADBq13i84fGTx9MlPvf4q91pih3gcVcpb2xxbdt2Ns9WK3t84DF33jBJNswNk2Bfjx9s+He4iMe5Ho96nOwxT/dmAAAwSst43JPalBAtldqmyrcWiVr1bxK2NXPDBNzoMT03ToJ5Pd7NjZNEPYP9Erbtbfz3e4PH4aV8nMdlzTYAADBiStjubuonlF/9U/8vuCPVJ5qwTfP4KjdOwPIef+bGSXCzx1m5sbF+brDB38nXHlfkxoYSsA1yY6J7vsCiZ21Vjw+7NwMAgFHKCduJTVmO9jjT4xmLJGIni6TpNIvhMg2hVndaDF9q3y2bdnnS4xWPg5q28y16mS7xmL9pb52d6jq3rudhj088drcYunzH4w+PYz1eK/ttZjHM+2v5vck6Xi9ty5X6QhbJ6vUeR9adit9SfVhzeSxt/RO2FT2WbOrzeWze1DM9py8thjF177t1b+6ihK1XQtg6z+I4epbP26zvEwAAjJASNv1jrnFS92bbuvwqGav/5LXfraWs3q66j9p3LuVfPJYoZW2vf6ukakGLpOXC0naGxwOlnB2V6jpHTTDX9vi52fZe+dXcsIea9o+asihhWbaUlXRKu8DgiKYsn6b6sA4rv/0SNnnEYrGFnpV65Pp52+J5v2TxjPoNeSoxHa+HTZS86lj3WiSMAABgiuQetjokWif610Sutte2PVNdPVSreRxssa/a1Bu3Uiln9fjVj6le7ZPq+dzqndMqUplhMdfqBYskp2oTto0sjnFKCfWyKcGr7eoxXPifvcOLqT4MJb4rlPJ4CZtsYvFM+9Ex6zPQ9at3LNNzrPf8uMflTV2RfWPxTuVV6/0OAQDAiOSErapzoLaxGP7UP+xdS1tOmlTX8J3mPdUesbr/6qWc3Z/qYyVsh6R6PvelHouX8uke33uc09k8U03YtrIY2ut1PaLVkPd5XJza30/1YejcOU7t2qND88du9HjCOvfYi1ayVjreDk29l0F62K5syroOrSYGAABTpNcqUSVZdWhzWvnVkOUepayk4LFS3ttirpi8XH7ld4+9Snk/j+1KWT1aGo7UUJ/mx4l6eDQHrZdrU13nVu+QrGJxntZzqS71/mqvnnqs1i3lBy0+YdEmre2KSF3nWAnesPRZlX7q8xNd71jDkvUZ6b195rGYdc/XywZJ2GZYfFJF1rDolQMAAFNACYOSrO+s8x22Ny0SlLXKPkqqbvM4ptRF27WCUPO/tMCgutoi8TneYv7Tx802JXwaWlyvadP51Dt0u40956o9hrxlkSBqjpp6w9Rr1mqHbislJ09Z99CiFjuo12jTUr/OIhHUNbW9WVqZOTs+v6HzaNjxC4/9uzfNND032Kw9h5US4Gct5ryph/EWi+HpsQySsK1jMR9OibQSQi2SAAAA/yN5WHJQWqDQJmyDONT6f6JCtEpU17SLdb4dNhmUuOkTGXV+2JxCnyqZ0+4JAAA0drRIjvRJjYnSZym2yI3j0Adm1XM0noss5rC1iw2GdZXF/QIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAMAf4G42h75a/JDuqAAAAAElFTkSuQmCC>

[image19]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAoAAAAcCAYAAABYvS47AAAAtklEQVR4Xu3SPw4BYRCG8YmOS0iIS+hUCKJRikSPI6hF4Q5UguAKwgUkensDiV54Z/cdZruvE4kn+RU7O/snmxX5nbIwpT0soUypdKFPWg4OlLcl7QoZsoY0crPwxQjGZM2o5WbxwpPW0IAd+afErcguaFKqriR3UgN4wJ0Kbi9sUT92JMm3U1obbjTnTOqwsANXjc42qMLmffpTkbY2CF7Ud7xAh6wJVdxMSnCkkyR/T4/+faMXhoAxCFW73nUAAAAASUVORK5CYII=>

[image20]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACkAAAAZCAYAAACsGgdbAAACOUlEQVR4Xu2VTUhVQRTHTx9Giz5QwT4kiIggQcgQi6gwg4jcBKlILnTlqk0tdNemgsAKiqBoVbRw0bZN9PGiKKkoN4qGRBG4EEGlTVSL+v89Z3hn5t3Xa9FC4f7gx7tzZu7cM+/eMyOSs7RphmvT4P9gFRw0n8HHsD8aUWQnfAhbk3jgG/wJX4vOQ+uiESJV8DJ8BCfhbbg1GpHBskjyPrxgknb4A260dh8cNTn2t5RPck60n2OH4Ia4e5EbcJ9dN8IF+Fb0z6Il9MIvcKVJzok+rMbaHk7OJI6kHUYhDTiqTd5/08WvWeywWcJ7iW+oRKUkn6YBR605C++6eI/onGfMiHrRTq6Er5G+gy/hbjfOUynJN6KL5rf4FXbH3Ytskfi1nhWd86QZcUC0cwquN8l5OAbXWNvTIn//JqfhHrvm7y+4t9idCRf0Aa42I46KPvB6Eg+JdCRxUumf3Ja0P8F7ScxzHM6LFlAmTaIP5Nbj4atm/GISJyHJtrSjDCNwIg0a20UXkVksgWWRJI+v73AgiTeIJnIpiZNySYbD4DPc7OIsxHHXDnD/ZIEeszY/E84d9s8I7vpXk9h+0UROJHFSLklWNOX+usnFWUh3XJuwsh9IscDIadhplnBQ9HWwkkM134LP4Qpre0KSLDoPK5hecbEuOCOlRx63vILoLsKiHYYfRT8/mskpKZ6zPEu5IftXxmoP/TzumCQXxvYhN470wlfwBXwCd7m+HSbvz3KdmZOTk5Pzj/wB7QWOxsWtJ2QAAAAASUVORK5CYII=>

[image21]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADAAAAAZCAYAAAB3oa15AAACl0lEQVR4Xu2WWahOURTHl2uIzGUeohQlyZs5IXLLHELiIokoD8YHeZB4IvFgSHKly5MHYyEyZZZQ9yKerye88cL/b63dWWd32p/vpgydX/1qj+f71tl7r31ESlpMX3gQbofdzCJ2wEFx45+mDXwKh8HJsNEc78b0hCfgVddWkTHwsck3FNMH3oRPzLtwem6Esgm+go/Mo7CT668VnRu4Ya6Hh+BOeAa+gUPcuIr8swEchrfhBfjdjAOogQ/hGtfWC76VfBDz4QvY1bVtg9dFn0G4r/lbgWOmnzNFdF5VrJIsgH5R30L4CbaK2vfCW67+Em52ddJR9JnTrL4FXs66f64Q7WD1LvCS6FmpilQAXNLXURvZAL+J/snhonOX5kYozXCPlWfCB67vlBk4Ake7+i+TCuCO6L6PCXOGwhlWnpcbobyH9VZuL7rNRohmHgYWgmNWYnptEakAnose7piVouPHwgVWnpsbobyDF119lOiq7oLtTAZ2DXa2MUtEt9Ykq1ckFQAPcFEAdaLjx8HZVi4KgIed+zrFbjjLyovhadganhe9F2gSH0D/qI8XCi+fmNWSbaGJVmYmivkg2RaKGWmedW1Ms+FFMO0yxdIk/1UAA6K+A7ApaiMb4RfYFvYQnbs8N0L5KJr/Y7hFeAfRgdbGVP0VTrX6YLjfTJIKYI7oH43ZB6+4Om/e+B7gLcxnTojaCd/qVjPAAD5LFgB3Q9UBhLcRYJ5nGl3k2rqLXlzMPoFl8L7kPx3Wis7lKnl4KPkJwVWgnnuSbUVuzXVmIXWi6YuZIgTwzNp4OQV6w+PwnMkxRQ9lECdF51P+yfjThG+5QfLP96wQTaE1omeD25P+NfC7hyuegp8pvJV5uZWUlJSU/H5+ACX3szSd59+5AAAAAElFTkSuQmCC>

[image22]: <data:image/png;base64,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>

[image23]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIgAAAAbCAYAAACnSMe/AAAExUlEQVR4Xu2aeehtUxTHl2d4ZMgUovxBhjwiFIk8s2QOPRl+zzyFzCFDCkmGRGav0DNlLoTyTOEPYyQiLxnzhxCKXqyPtXd3nfXOOfdcv/u79/er/alv7+61z++ee/f57rXX3veJFAqFgdlWdWQMTgGzVY+rVoodQ+Io1URSYYjcoFovBpW1VCeqLlNtE/r+DwtU+8bgkHkqaevYUTBWEXugt8eOFh6MgcRmqmdU/6jmV7sG5nix7FHHhUnfid0LrV25osqqqk/ErlusutH1bZz0gWqWixcSxSDFILWwRPwolsZ/Ut1R7W5kZ9UZMRiYrEGWVf2g2id2BKiF3hG7H6+bOED1ker52OHA9KOoq2YkX0p3g9yiWicGA5M1yFzVt6plQjxytupcsfthgsiWSbuJXXNJtbvCIapFMVgwuhqEmf1IDNbwl0zOIFdK8/LieVi1gdjDPzX0AcsUOlzsml2q3RU2VP0ttuQOzKWq91UnqbZIekz1hupVsW3Y0WJp6i1pd+p0pKtB9lCdHIM1eIMwy3+WXq2wg+pF1ZtiKX/TdJ3nCdW1MVjDC+nfxaprXBz4rOsm3ST2mVasXLE0f6h2jMF+7K06T3WW6nexLR5aIfWTCt9VHZHaDAADkYufmcAX0s0gt6rWiMEavEEo/C6SnkGY9SunvidVd6XXHsbznBh0UAyjXGwukmrhTBY41rWpU5jI/WCisNQMxM1iaexO1edi2cIf3GCQ21x7e7GBYGbUzY5B4d7sMgYRZh6ELhmE5eWhGGwAgxzn2szmbJC9XJwH/J5rZ/g8ZOQmTkg6LLUfUL3W65bzxbIFRkQsHde5/ibeVp0Wg135VCxzeHAxX3p3F6No+tq1PRNiJntO7EEy6Gjc8ECYAG2QSTkE60KbQea4OOP5oWtnPpP2HcX9Sfmw7mrpjfn6qv3Sa54L4r77p1gbLHs8v4HhptzkoBA/RZZe27hJ25nCN1I11HQAg9Sleg8G6rK8QDTIXOkZZHMXxyBsPyPUcYxtE68kZaiLlogt+xyfZy5O4r5rungTnJWQmQamGKQYpJW8TYo3uUf1kmtvInYdKW7XpAnXT01CoTvbxfqBOWON0U8X/PeX3elnkOVVC2OwBcZgvmvnNN/VICzBFLZ1UPjfl5ThQI33Zku7kYs/m1RX59TxvWrPGOwCxRSVcIS18nLXnie2VcLJ+UcgP+v4AnlrNp3AIHfHoONA1TEx2AIPq6kG4Yggw7h+7NqZ66X581whNuZ+3DEd781uM8NG4pckf7TeBJOf91g9dnRhger0EMMEOG4rF+PN2bo9LXZ6hzz3iqW8CFliHJD9XhYbmF9Tm4cTYbbye0Y/dlK9LvZ+bJ2vEjuWxwTZIMxmzEZGYvyIcV8/89npsCnwkIXINly/JIktM2AGfkvJmZln8Jv07vmn9M6rmjhY7FxrrDBTff2R9/OHuth0g0FlGzlKllN9JdUdz1RDEvBZb+SwdlK8+aNcTvhQm7PHDeZl6Rw1Z4odzE01qyVxnjVIbThU+E8vj4r9epoLSdoc3nQ5wBknLIvjMDCFMUfx28WOIcP3Q3U/9hVayId4o5jFTTCzqVVmxY4hQWbk8K/rAWChUCgUCoVCoVAozHD+BdwsLAoLTdHsAAAAAElFTkSuQmCC>

[image24]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFIAAAAbCAYAAADve9g/AAAEA0lEQVR4Xu2YeahVVRSHl6VppoElIiEmKigEDuDwhyZPRSNx1jBUQlQsJIKCssEBHBKUJkJRcC4cyxxSNMsINShLlCwKFUFJxQQRMVGR/P1a69y7XO+ee+/TN/TifPDBPWufe8++65y99t5HJOM/yzLYOQbrGS/AiTFYm0yDs+3zg+Z4OBMOS06qJ+yG3WKwKjxgzoCvwKfhF/AqvACXwsampzv8HT5kx03MJfCW6JNamyyAh+A/ov1uZCawvyesnf9tvWsjneDPsEGIl02WSOW+EvkE3GO+BSfAM6LDcir8UfTC80wPkz0rxBL2S+0nkoyCZ0X7PNr0MEm/wdYhnrAZjozBUrSEv8IxZl94HfZ05zSHl0TvJPXxv2EHF/N8I3WTyPfhWHgb7jM9j8HPQ8zzvGitLJuG8Du4yMUOinYkskP0DlMOXTIYns+dURn+gbpIJEcCJzwmK+lzR9f+LHzVHUd47g2pXMZSeU70Iq3go+Y40U5E1ki+U0n761L5bntiIvm91+BP5gG4HT4VzvkIHjb5G8vhHPil6DWLwVGy0z4zYUmf5+fOEFkIe7njCOcK1veyZ+9tooW1HNi5H8yEj+EGdxyJidxisYdNMgJege3teLJoaWlhkpXwe9ERwPZiPCNa5wlrISdCyprPBJG9oqOxGOdEb0RZ8OQ4axWCHWLxftlM+EQ0mWn4RLL28snol2/OwclsjX3+QPRPe7iK8CWlGJwMK9zxGya/PxQ2g7tcexrHpPRN+xfeEf44a2IpBsI/YVMzYRX80B1HfCJZk3i9NvnmHF/BI/a5QrQ+tTUJhzrrXjnwmj7hnEwpn3KuSgbBt117Giw9L8VgGhfhNcmvAQvBgss/OTw2gPfg6hh0+ESyNjKRhWZ4nnfSPrN9Ldxkcpi+KeUVfiYwrWavE73+Z7B/aCsE+8PdWVlkiUynSonkjMkfXxwbHOzA3Bg03oFbY9Dh15Fcl/JavfPNOY6LXodw/TfdtVUF1l/ubArBnRqvz7KRTHTFuAz7xGAaAyS/PHjXrDD5JoSL0mJvQ7iD+CUGHXFnw1mbTxlnz2QG7Sq6lUueVD4tXPZUBNtZezG4LeULlDSOwm9jsACtRXPi54OScBXPCyQJPQE3wklSepZ8RHT38LiLcVakHGK8+3+JbrkIz+cExRUA5Tlc6He2dsJ9MROb9MebthsZAv8QPeempK8k+KSnPbEerqW/jsGahk/YizF4H3Bdy41CpAs8JbqEqWk+lSrUx+qih+hSoTrgepW/NSE2iO4yTsvd7wBqAo4ujohSC/YagcNlSgzeI9yucnLjlo7y7dIK0d1NocV8dcOnsU5fRrPQPxmD9QwO58kxmJGRkZGRkfF/4A4msfuwH7YSFAAAAABJRU5ErkJggg==>

[image25]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABwAAAAbCAYAAABvCO8sAAABhUlEQVR4Xu3UPyhFURwH8F+iCEkRBklSFoykJAODyPAyMBiUMhiwShnk34DBICkWERHqWZTyJ6vIwKBkMhjEYJD4/vx+573zzvNKue9N51ufer/fPe+ec+899xL5JCkZMAFhuFOrUGEPCjIpn3AeGvU3T8KeSCbONoOCSi58wprTH4Uv6HH6/04+ydVsO/1WkgmnnH4gKYJ0p9dLMuGg1rWwD4dQqKZhB26hG0phBY5gV1Xyn/+SDXiAHK15skx4hRtVo8eGScZuUnT8qZrTOmEa1Ds0a4/vwCKUk1x1nzIZgTcotnrHasHqxaUE7lWnc4zDt/mDZKMxE37+fAdMskgWzEJWPya8/c+gS3HyoCUygmgJLqza5JnkKk14Z/PCzOJ+TUonTIMtqHP6TTBk1dcwY9WcKpLnWm/19uBAcZatYz+ZhXMYI/nqsHW4gjYdU0By4natTfrhhWJfq0eShbIOkl0cSRnJiRIx71E1XFJ025tMkizQzgCcqHGKf8d9fHx8kphvOqlcx8kHwZ0AAAAASUVORK5CYII=>

[image26]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABIAAAAWCAYAAADNX8xBAAAA+UlEQVR4Xu3TsY5BURAG4CORUJCwNEqFQuERvIFGtdFIVraj2lriBTbboENCpyQSBbsvsAXFllSeQbUR/rn+wziRWwmNP/kKM8ck5965xjzzsOSpBxGnZ/NGY/iBEWRsswB9mNIeYrap0oANZVlbQvd0gqmRDIo7vSRs4YMkAVhB2x6y8Rv0znqafOM3aAD/UKZPGMIXBNU5L1W69ozmsIM62XxDU/32crNB+movTm/CeopsOuZ45Yv4DZI/SN1Ny1yp60EJp1diPUo2srxy5YvoQbI3OmH4gyJJQrAwxzfnpQIzWJMM+mVN70zOnLdfevKJvKr+M/fIAZc7Q0JGv2hMAAAAAElFTkSuQmCC>

[image27]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAoAAAAcCAYAAABYvS47AAAAtElEQVR4Xu3SMQrCQBCF4bFWKzsRLLQI6Em08RgewcoLCGJh0NYDSNpAEG0FTyAoFoK9jaW+cd/ABiRsl8YfviLDBLJsREqvCw0qbAVvOkEGKVW9PVnDi84whzrl0sUmFRa8GEvg4hJmpAe4wYhyLWBMWg+e1LYlreU/sCtN/WHw4q+OlNigA3cYkKU3pLY26Iu7uiFZD5rYIHixAhtxl28/gL5woRpn3yI40B524r5d/SujD8nXLMmtxSL9AAAAAElFTkSuQmCC>

[image28]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABUAAAAZCAYAAADe1WXtAAABKElEQVR4Xu3ToUtDURQG8G9OwcGCQWwqLuuCawZ5sG7RNFkz2BVFQYZlYJh1xWgShwaDSVaFCSJrtg2Df4V+h/tN37vvMtOC8D74hXvu29k9231AlkCK9E4rXn2Kjume7uhENfNnJtL0kr6o5NUPqBVbn9K5jM069eCa+id9oeXYukAfEkxOHmgL4ab2Zdc0q/UaPUkw+1KjCOHx91R/ow3qUkVSmacbsUQIN7U04PaMPZ+XVNpwo47GjRBuWoU73TYN4J5pSiI2xplXi5BsOi1DWlJtkZ71XOr3n0jTi9hGyBVtStd95Ccz1Jcdby+VXSRPatMYO5kfe7tM2d/wU0ey6egftnt6iN/XcpU6Mja3cONY0086iu0t0CO9wl0nuzVzkiXLv8o3xgtOsvZcLr0AAAAASUVORK5CYII=>

[image29]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABUAAAAZCAYAAADe1WXtAAABLElEQVR4Xu3TO0sDURAF4FFRi5hOrH20VjaC1a0CIlr7wFYtrFMpiGiRJtiJILaCaKGIjY1gq4ggWiT5Af6FNHrGOdedJO6mEbHYAx9kZ2Zn95JEJA8zQDtwDzcw7wfaMgQ1GKMf8+tLe+CCNllbg/r3RGeq8AHj1JF1eKaYA3h11z5T8CC2NPVN32CfukVPdQ0LkrF0Qqy5R6fwJHbjiJuL2YBlCJJx/CDWjMcfhF44gatk7CvDcMbPQTKWzoo1dylmkfVJVzuU5KhBMpZOizX1WCpmjvUlmKFt1w/s/93SIjTFflYqJi5dgQrpdZpjuy3JHWxRjH7DOjzqaj76sNQ31ZTgkfqgHy7hyA+1ZVW6LNXokLqFhthfttAykeQcXsSWvlO5ZSJPnn+eT4iMUqULeM8tAAAAAElFTkSuQmCC>

[image30]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABUAAAAZCAYAAADe1WXtAAABLUlEQVR4Xu3SrUoFURQF4C1qEIw32RQUDcJVgz9p1GQRwxX8TSIIBosYBKOIxWqxaFPEZPAJBMEkgkEfQJtvoGvNWXPZZ+4wphuEWfCFWWdmzzlwzKoUpBfeoT+/gBzDCzzBfm6tNG0ZegY/MJDrt+ABeqAbruFQSjMOzxaGZjvtkA9YVccswLd0ub6Z7MN7WLR46ISwm1XHjKmjSdc3syNrkFh8/CVhN62OGVFHy65PU4MbYRKLh24Iuyl1zJA62nZ9mnMLR82Om1g8lLug/NBBdS1DZ+DIF9Y6dF7yxx9WRw3Xt2foqVsocgF9wue58Fmauntv1PWFWbd4p1neYMU9855+yp/ZtOKhu3AHnRbu9CWcSGlu4dXC0C84iJdtD67g0cKt4Q+oSpV/lV8z3lQREFFgoQAAAABJRU5ErkJggg==>

[image31]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABUAAAAZCAYAAADe1WXtAAABUElEQVR4Xu3TvyuFURgH8EdIBpsfsUl+FpGE8TLZDBRlE4vBYmGQBYtSDGY2krIZzGKVSFEymeQfEN/vPd9z7/O+95aFQb3f+gznuc973nPue45ZFqQWduUS7mAH6nyTsgm3cAMrqd8S+ZNJD6BXmDH4hKNCR8g8XFhYRDUcw5ok0ghfsCUxp6o3QIU8wazrmYAPqXL1/KTvVtx+zKqFSbnqQeE453oGVKNhV8+n2Yqridmz0NwGk8LxqOvpVo2mXb1sKuHewn/GzAkfHolNSIdqtODqZbMIL9CkMVdB6UnbVftx0j54trC1mHFJb79LNZpy9ZL86qT1cg1DqvHrtkKL8GGehph+1Sie8UJ4kM+FXztmA3rc+AFm3Jjn9E1KwhvFm0LrsA8n8Ao1rm8JziycDh6/Q9iWRDqtuIW0R9cXs2zh+l5ZWAxfQFmy/Kt8A0goWPH6EyiyAAAAAElFTkSuQmCC>

[image32]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABUAAAAZCAYAAADe1WXtAAABTklEQVR4Xu3TPyhFYRgG8FcYjCjFjFDyb8Ak3NKd7h0oZMOkGJjMZDJjRES3DAZJNqWMlCxGRZJsRp7H95zbe+9xS8mgzlO/ut9z3vOdc0/nmCVBqmFbruEElqDMDymrcANXFmZK5k825Wabwo1q4BXW/RAyDadQBZVwCMsSyy28SxTeybN+80J0DxP5CbM0vEmF67+SsTAcncANHuFc6x75gEF1TJc66nV9LOWwaOHqHeqywpP71TGt6mjM9fk0y7GFxzDjjk0JT+5zPeejTWdd/20a4QnmteZdUPGmTep+tCmza2G4DYal+O+3qKNR15fMrzath32V/sCKheFJaBCuh9xMpzpqd72NqDyQKFvqB1x3B+NuzfeUz54KUgsvkBKGX9QDXFjhpzoHRxZeO/b8Etcklm7YkzMLF8lBnR9SFmAHLmHDwgUoSZJ/lU+VNVpJ/7K73wAAAABJRU5ErkJggg==>

[image33]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAB8AAAAZCAYAAADJ9/UkAAABkElEQVR4Xu2VSyuFURSGl9wyIZmZoMTExF8wYULKwEDGfoTCQBK5DJgoZCjXmYFbco0MXJKJkgylEIa8r732sc7u7DN1yvfUM1h77fO9fd9e7SOSkAM0q5dhQ2lT2T+Ei7A8bYejBh7AI7gLG9LbmfmT8Fm4A7fUl/T2D/XwQeXDSRc8g8V+EyiCV7Bd6zr4CGvVKL3qW9gAM3BB9eTBJ9hh1rrhvanJKpxUo2QLZ8iwauFbTph6SdyRWKbhuRolFl4Kv2C/auFnXzH1ibijs4zDZzWKD38N1ivFhfepFoZtm/oabpqajIr7PS0Ieilib14h8fBjcRPt4acNw0fkN7ww6KXw4e/Ber64Hw6ollO4bGoG2y9BxsTNDI2SE+EfYUPcxcKzoxZO+6Cpp8TNgYXTvqdGyRbOh86rFg5ni6k74Z2pyTocUqP48M+wARrhrcrpJ63wBpb4TaBM3MQ3aV0l7tLhFZvxmu0Rd1b++uT57usaz9vDB9I5uCFu0v1Va6kWt2cNXoj7v0hISPiHfAO9tXoBDGrPKwAAAABJRU5ErkJggg==>

[image34]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAB8AAAAZCAYAAADJ9/UkAAABqklEQVR4Xu2UuyuGYRjGbzllcchmQTkMGIzYLBhIGQxi9TdYMDhFDgMGA8kkx0XKISmnSHJIFiUZRfkHuK7u++273+/ASPl+9Ruu53m+937f57m/RyTJHyINXsKaqPEW8wYew2WYF1qhFMMjeAIPYGV4+nt+tXgP/IR1bqwcPpt8OOmAFzAzWAQy4C1stVwGX2CJmZBSk2/N4v7L5+CiGZACX2GbG+uETy6TdThlJmTbrBctXuvmWGTE9PArJ11eET0Sz4zoMdK4dMFus0rC255tuc/0cNvXXD6Dey6TCfhmxpALt0S3kUYXL7Dca3pYbN/lO7jrMhkT/T1lM4eYhRUuRxfPtxyv+KloRwdwa6OLj0qkeLqfYFMN+gGJLZ5qud/0nMNVl1nY7wQZF+0ZGuJXiw9LZEviuWPreLHw7KiH3T7g8rRoH3jY7YfmjzRK+MsJH7pgej5E1we0w0eXySYcMn+kSbS4/59XwweT3U+a4T3MChaBHNGO511BCkUvHV6x316zS+aVaPF30fMK4APpvOhlxE4PrlpPkeiaDXgNG0KzSZIk+Td8AUw7fufKxUCzAAAAAElFTkSuQmCC>

[image35]: <data:image/png;base64,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>

[image36]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABMAAAAaCAYAAABVX2cEAAAA/ElEQVR4XmNgGJGgCYgPQ/F/IH4DxBxI8hpAfB0qB8JfgXgLkjwG8IbiJwwQDVGo0mBwGYpl0CXQQQcUhwHxXyA+hCrNwAnE26GYIKCqYbuhmBWIlzNAvKqNJG8LxHVQjBdwMaDa6sQAMawXroKBoQqInaEYLwBpRrcVFNDPGSAuBYFtDBBLQRgvqAViFyiGgTwGiOtAYcjCAAkCogDIVh4ohgF+IP7MAEl7VgyQyCEIQLbuQReEglkMENetAmJfNDmswAaI29EFocCUAZHqhdDksIIJQJyFLogEjgPxWXRBdOAJxDcZILb+BuLpUIwOEoF4IrrgKBgFowAGAI9RN//FLTCvAAAAAElFTkSuQmCC>

[image37]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAoAAAAcCAYAAABYvS47AAAAe0lEQVR4XmNgGLrABYi3QDFOwArE1xmIUFgAxOeAeDMU4wQEFQpC8RIg7mPAY/UEKFZhwKNQC4g7oRgEcCpcBcS8UAwClCn0AeJUZAEGHAr7gfg/ASwLV40GljNgMREbIFrhSgY8MSMJxbuB+CUDwn0ngVgUSd0ooAcAAOPaLf8lRW2HAAAAAElFTkSuQmCC>

[image38]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABIAAAAbCAYAAABxwd+fAAAA8ElEQVR4Xu3SMUtCURiH8beMwkU/QGBDezQ6heDiGDS5BA3SEJSQo5MgbRJ9AEEcGmqNoD0iGlxcjYYIWnOMyOe953/tQI1OcR/4De+5nnvvuWiWlbW42hjhQLZxjUfcYQVHGOJBDpOdUTWc4BQfcmZhs/P5CVX9fk++sKq1pHOso4+xrOma32iKjmZvVz6Rj9bnTdCVtDK+LRw1rSf30dq8DQsb/JgurYV3LGtewrP4d/3Vwm5Ut3DmgqRd4iqaKxYe6Lawj53oul3Y32d+w3E0N/EiOdzaz9smDdCIF6iIV2xGayXciP/P/K2ysv5xM9V2NGlILvDIAAAAAElFTkSuQmCC>

[image39]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAoAAAAcCAYAAABYvS47AAAAsklEQVR4Xu3QsQpBYRjG8XdQJjegyCK5BCbsJgaZrcpkcj0MMqhjMjAod+AClMFCGaw8T57Xl050Nin/+tXp7T2n831mv1MOItnCDKry0gL6wjpwkZIvsSOshJXhJkNfYokXu9AQVrOw2NQsVgbmFg4Xqy4bOEBePtaDvfDq3pZ4MW3hMGMfFmACFfH8izsftOzx5khYCq6y1Cz5YhbOUBTWtvCPfH7G+5vKGk4wkH/f6A4uajZuMFfIFwAAAABJRU5ErkJggg==>

[image40]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACYAAAAYCAYAAACWTY9zAAACWElEQVR4Xu2VS4iOYRTHD4aJGYNyjdQUslQWrlFEuUdjMQ0L12RhIc1GsUC5lFsuEYVccisLNI3FLIyMSyjKgrK0nChkxf/f+T/fd773e+dCkfL96lfvOc/zve/zvc95z2P2n9EET8B5Mo8JsDmb/JM0wouwH2yV+2BtmLMcfoQzQy6XGngSvoP35WE4NE4Co2EbfCbb4fySGZ5bpOsl8hQ8DXfDo+b35xvtkSPwjvm/TD6Cr2C15jD3FG5UTEbC93CB4j7wG5yhuF4eUkw45xqsC7kueQx/wLEhd1y5OYpXw07zG0f2m7/FxBc4S9fj5YHisG2HDSHuln92YQvhlkzuFvwKhyu+At8Uhwtsg9/hIMX8k8t0PVduUDwJ3tD1L8N6oayVWE8PzWssCx/KNztR8TrzGmJN3pTDNHYPjtN1r2EhX4af5VnYN4y/tPyFrTdf2LSQ4/byS0xvjHAe3y4ZA4/BXbBK9sgQ+QTehv2VZ9zdwtKXmAfbTIv5W+QiXsDJ5q1mj+w1W80fuEMxb/y8OFyA2x23Mo+rcKqu2eP4JxOpb5YxAl6CmzL5xeYPZL0Q9rq3xeEC3J5Plr8dvAeNzXQnfBDi87Ksr/Es4wLYsSMsYuYPKl5hXntZ2DzvZpPmX2mHjCcIdyAu7IwsW9hg83NrreLU+dmb2JPYuQmPLW4l+1mCXxtbyMqQS+yFq2RkqZVuJbeZ5sJCPGd+4H6QPAunx0lglPnXel2yiDeXzHD4uwvZpBgIX5s33tnmBzz9K6wxr92umGJeu2wXA2SFChUq/A4/AWHSgHs8udYNAAAAAElFTkSuQmCC>

[image41]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABsAAAAWCAYAAAAxSueLAAABmUlEQVR4Xu2UvStHURjHHy/FQAbysv0oZLAoE4OSycQikYi/AItSZiWDl0FhwPJTConkZTArkkXZLF4WiwGJ77fnOe65p/srk+l+6lP3nvPc8/ac54qkpPyBBTgGO3JYzCBjxNyH53AP1nv9JXDWZMw2XIRlLuAQfufwDZZb3Ax8MJus7Rqu2TM5gu2mg4vbci8XcBIOm92iOzqBgxZTITrxuEny4D1ctvdS+AGrTQcX+8yHAjjldTh6JBqU8Ji501oziXzRQU/NNmsfhZsuKKRB9Lx9NuAnHDLnYBbOw0IvbgC+m1wcc7orXs5CLmFX0MaVfsFp03EmegEcPG7mjd6ITvgIW72YGP8yWa/5EnaAA9EPa0zHqujx8nKwRDhBp8kc9sM7+OQ+cOyYx2GH6KCcLGRJtJ21xlwyPyEZSdgAG+h62CG6Qg7KHVAHY3m8bOOtXvH6fGIXLiNRIbu68eER3YqWBCVF8Er0RpI60WNsNB0tojn8pRK+mhN+h0ezRMlnwfN31ReLEKmS6HfFXbM8Yr+rlJREfgBho2ri9AlCiAAAAABJRU5ErkJggg==>

[image42]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACkAAAAWCAYAAABdTLWOAAACLElEQVR4Xu2USahPYRjGX5KZDCFkqEvEhmLJQhaGsBGlhFBCZFpYUOYspJQylUwp81WGLq663TItFBbKVFI3FiSxILnP432+7ns+R1w7dX71+3fe4f+d7zvnO59ZRUXFP9MN7oOH5Ba4FXaMTWCpvACfw/NwfKHDWQ0nmY/bFq5R/DcskVfhTXgxFfbDXSkQd+G1EM8zvzklXMAl+AEOSk3iM/wRPAk7FDrK2QZfyGGwHXyVig/MB+siyVnlBii+Dw/KxBjznt0hR57CTXA5nJzVfkcf+Akuk6QTbEoNU+HiFIg78I356yJ89I9kG+WGmk/yuOIEe1sLJ8ax+sk/Mgt+g9PzQsYi84H5xCL34Dq42XyxCwvVck7BL+a9dI/5nt/e0mI2GO6Q3FP8gLrHhgzusWfmWyVtkcQZ2FvXw+F3OLelXMpt+BVukImH4fr/mGSkL3xi/qryYyjBRdyCPfNCCY9hQ57M4EnCrdNLJs6li1H262S4Gv5pZZYnq+AV2D7Lz5THrPh0udiXIS7jqPnXnXOaPxPMJ1NbrNkK5TeG3DTJJ9hZuR7wsK6PyPewv3LkNbwc4jIWmN+PC4+L58djNeZf8uxQYNN1+A4OUW60+cFKeejyHKQH4Hr1zJF7FRPuRd58XMiR+eZH1UDFfPI8X3kcUtLVwhuYAnfCE/ItrIcjU4P5ALxZmTNCH1lrvgcbzScysVj+CY+nj3BEyI2FdfKG5NwqKipaSzORoIfIr2VVkAAAAABJRU5ErkJggg==>

[image43]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACkAAAAWCAYAAABdTLWOAAACBklEQVR4Xu2VP0iVURjG3wqyskDBySizAgchHBJcRKUloyAcHISGAkUc1CEItFJoScGmEK0hKWiqaAlECnRwsJRIEMS/k6CTtLQ06PN4nuM99+i9XsFF+H7w495zznu/+973e7/3miUkJBwZp+AkvB3tN8svcAl+hpVpEQ5+7iN8AV/D2rTTzFTBT/IPHIeNYUBIJ9yC9cFeE+yQ5Az8CjfhJe2VyGV4VXt34X9Yo3UmrsMP8KQkT83lkYb/ElaRh2Elf8Jh6akwF9en9X3JvZdRzKDWmRgwV7liSZjshg/w8DbSWtub5Hc4K09o74q5uPdaX5Bd8Jr2WEnGtGqdiR74D5ZKz0Lw3hpgt2Tp49u9Hw/NxbXFB+I8nJCno7NcYMvs3u48OKZXmkuSjFuEv2B+dEYewG9wzXJ/cGLYo+z5HY5Fkr2wbvcotyTfwB+wMD6I8JOC7XQYGL8Cb3Bx2VKN7zkoyXZzVYr77JwsC/Y4c/+ae0r9aMnGTTlnqdFmj+Ar+CyQA5hJjsAWHwjuSFaQyZAC+FbvRyU/Gw75dXNPLhPORgmckSxUVqptbyXL4arkP4n/QUPwsWLYAnQKntXeLXPX6tfaw57lWLuoNft62lyBaFi0NN5JDm5e+Le5JMi89vbznmKKJMcYh/m4ucZ/YqnZ6nlurg18a/DHxdf1JiQkHJZtDoGDIi2fK54AAAAASUVORK5CYII=>

[image44]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACkAAAAZCAYAAACsGgdbAAACOUlEQVR4Xu2VT2iPcRzHP2MhbURZK6slJ3ahMGlttd3sZq6ykIOb/0W54LBEKbaWi7acHDi4sDZbKw4jkVDU5ICD5ERy4P32eX/8vr+n3/P4nRb1vOpVv+/n+/l9n8/zfb5/zEoWnuVws1yU6VtQeuWLbAfYBn/KL3BKXk9ygp3wEZyBN2FPdfcfFsOT5uNMwIPV3bX5p4u8Bu/De5KFZNkOv8kf5vmHYUOSs05+gDsU22ee3xVJCePwrH73w+9wpczluGSR6cNJJ7wg89gl+f8hxTapPRxJYi98a5X1fQR+hqtlLkVFbrW/F9ksT5vPKOEMcbxDkSQewyuZWF0UFbkF3pY34AP4xHym8lgDp83X5hLF1ko+45L5J5+Ds3CDcgo5JmutSRbzXK5QjGvyjfnxlIWbgC/xDrYnca5Vyme8Np95csZ8bL5MvFBNimaSa6dNBuvNc/cnsSx8kY+wQ+0+yf9djiSrnB67ZS5pkfUc2JwF5o5mOxI4y8zhkUTiQmCMx0/AT83YOZnLf1ckD9qUW1Y5R4NV5rkjag9KboYWxQjXJfOWwmWS5+2JJGejcs7LXIqKfGa+A2kQA+9RO24hxroVa4Rf4Xu1g7vwYtLmZcH/8baiuaRFcvAUnnNxWAdXzYuKTXZK8tPGDh00H++o2gFvoJdWyePXmDYfK7tpf3PA/O6clxz0oWJxRBAevpSFPYVjsCnp54tR7ug75mfpJ/O1V+vBA+bPeAUnYWt1d0lJSUlJPfwCCQGci4ZKtLkAAAAASUVORK5CYII=>

[image45]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACkAAAAWCAYAAABdTLWOAAACUUlEQVR4Xu2VSchOURjHH0PKFBkSyhxlKJRslK9YmJKsWIiFsCEpQ8jCFAqJLGysEJGVWZlKWdkolKFIhgWhLFjw/33nf77vvLfve0tW6v7q9/ae8zz33nPPOc+5ETU1Nf/EKHnS3pe35JoyQWyx5+ROeVyOaMhIzJNn5R55QrY0RJuz2l6Vt+XlHBgsP8l9FtbKn7Kf28vkTdvHfYfkWznI7ZH2pRzjvkXyl5ztdjN4Ka7FcbK7fJ2DB+Ub2dXCJvlZDnD7iPxtF7hvg9vL3V5i6Tvgvqlus0LNYKK+y3UWesr3/Oki30VaumZMlNssFwMzyQCIQV+7XY51HzNJTn5wZxAnb4htgAcQZDaP2aPyhpxc5FVhOXjL/dVAAdvinu1RiVU5I3/IVfawvCT3EpwbaZAvon0mYKn8KAe6XbJLPpcP5ehKLLNCXom0Si2NoQ65E6kGNtvMY37+i0HOijRIlrhkmvvXV/ozVN6FSKfC+EqsZGOk+/DSzbgWKY9CzcUKF/lhgxMsRw/sR/opDhga6ajJxw3MjJRz3u1edkJbRkQ3+TXSquSToyNOR6ruKpzJrbDUu4sATI80AGaCTc8NvtnMFOdw8MJ1S9+MnCQ+RCoKBtwZKyNdx7PKIqN4WuHLQgVyk3wjlvmVHBZpBp5GOqbKo4oX48aL3T5lH0X7MTXHOXlFMuxZvijD3e4tn8n5FjgdGEMblPoDyyeRwfQv4pOcg+zfJ5GKZ2GRk7fDjkiH+V35RW6NdB6XUHxsg3JrUAf5q8YYkE9sTU3N3/IHhlqPj2BrJ7kAAAAASUVORK5CYII=>

[image46]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACkAAAAWCAYAAABdTLWOAAACP0lEQVR4Xu2VS6hNURjH/97vQqTII5SBCUWZXTJBRDJSQlG3O8CAbnmlGKBMJHkMRGHiNfEmlzLwynVH8p54jSRFMeD/P99/tfdZzrlhpvavfqe99veds9da+1vfASoqKv6ZHnQ9vWjP05N0cjmJrLXn6At6ls6sywjm0VN0Jz1AZ9dFu2eNvURvIOZSYwfdgJisFDPoI9rT4+WIhUjRn16gn+hY3xtvX9KJvreQ/qAtHneHFqXvSm1Qb/o6BR8gfiznDR3t6/v0sE1Moz/pHo+XWN3bneUc9LgZI+kX2mrFAPo+JWhHntFlVsxCTD6hre+yabcnICZwwuMhdjOd5HtavHLSg5uhuPJG2d+YTt8hkuRVehfFa2zGakR+Wx4wg+lt2zeL5egMfKWr7D5Eze9KCXr3KvCHVg/+hmJXG9GPPkfs9qAsJlYgDuFb/NnBuUW/00028Thd/BeTPI6oo8QcegfxJZVCI47Qm3RYHshQ19Cil+aBjMuIvOE2cUYfOupabZ9SQKieOlE/+cQ6xC7ldTbQTind60U/048o2lkjjiFOd85pfbTQJ1kgodZSPhQLrHZQkxFD6VFfX7HakXKT/4A4FJpwM1YivqeFlxevw1OrLZ2+xaWAUH/sQPE6pyIaq1TT3WYP0Y3OUQnIe4geJ+YiHr7X44RqVm1tjMeq66d0vhV6m698XZv5Vrrfavaq03EpAfEDelgjFzlnhN2CaOYdiH+kdhS9NbEdUQbl0lD9X7PXrf5iKyoq/pZfR1GOLXOi00UAAAAASUVORK5CYII=>

[image47]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAWCAYAAAChWZ5EAAABq0lEQVR4Xu2UPyjFURTHT8i/woDC4imE2WJgkMSikEFRLNhEiEEGoliwsPlTBgsyKRM2MimLMGJWFgPf7zvnPtdF723P8D71qXe/9/i94/3uuSIpUvwT8uE63DTn4RzM9Iv+oAzuwgt4bU7BDK+mAQ7AGpNUwWVXsAGX3MLgg46DLCQbHsFCW7eY73DRFYk29BH4BJtcAb+MYZZJDi0rckW/0AnvYGOQ82/fYIGt2cA2nDZ7YantRWmHg34AruBDkIXwv2WTPUG+Y3nE1hOwLbabAF2iP2NruBGHdPMePsI0y8fhGpw0eWYOYLHtRykXfW/0VfRc5PkFCTBshr8KPzP3YROXfpD0Bnw4Wreio+UOZTxqRU825eGMR59oo1HqREfKZ0a0YCjIf4OTciNfY+iTA7fkZ1NcRxvgCPED59ln1PKxIA/hZXUKO4J8FZbACtHnLHzflhHLpVL0xHd7m+6hz6Kvg9TDMzN2gYjON5ufDXTvl5PAVxmxNckVHfN9F/AeWIF75otoA9WuADTL1y3Gi4T0e1noudWQCDwRfSbll/Ow8/WkSJFcPgF65mfzAqOdzgAAAABJRU5ErkJggg==>

[image48]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAWCAYAAAChWZ5EAAABhElEQVR4Xu3UPyhFcRQH8ONvYjBQZPFioYyMlD+zEgYDA8nMoCiLAZPIn1H+zP6sKIUYiJTBIBkNNoNF4nveOfe9c083j7c8w/3Wp949v9O75/75XaI4cf5pCuASOv1CRGpgG87hRk1CoekphgU4Ug+wBlWmJ5Rx+IIuv+BSAgdQocfczz5gLmhCVqHFHCfgEU5NLZladUEyQKY70EPyR62uvg/vUE4y3BuMhjqIJkjOEcqe4hP/ZgC+Wu7rd/UtrSdIBniFFduAjJAboA+mVIMuZnoEPvzusCd4hvzwcij83qQGKIUTKFLZDjCmou6KTRNJz3JQyPkAs9CeWs5ugEZ4UfxyRqVM3ZFsyzwu1sOOaeL8dYBKuKf0NowKn2xXTduFYViEGWOdZIANkrf1p/BH5hi6XX0Jqs3xPMlVsyC95nco/Dj8Nmwm+XCwNlPfJPkY2QtgV6ZniOS2+55D05MMbw12TTLALaX3b4fW2IDWBk3NO9OeOpIvo19nn9oTJ07u8g2deGd1PXLxHAAAAABJRU5ErkJggg==>

[image49]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAWCAYAAAChWZ5EAAAB00lEQVR4Xu2UTyjecRzHP6Nw8F8pi6QtipIiJ6yWVhy5cFqbw2wXiZJdKEK2CGXSkoubIgcpB2G3tR122MWS1Iy1IoqDA++37/un7/N4nsWJw/OqV/0+f37P79v3+Xy/ZjFiPCAK4KTcgKuwJaQjMkVwBn6EI/J1SIdZKhyHU7IP9sCEoCEH/lOBknfwDCYFTVH4Aev1nCEvYOd1h9knOOjF5BtcCgKufgfGSdIF/5pbfTSyzH2MO+ZzBL97MT/GvkRJFpSzR/A3HFPhrryFz/WcKfnDs0EDqIOvvJh8hdt8KDH3wpC5RdBRuAKLg+5bwvfoLswNq/k0wHP4gkGtuQX8gsmSNME/MF3x/3gGP5ubGfomtHxFPhyQJ+bmIoWFe19AlbkF8Pj4VCof6ceiUSNP4Yewms9j+BNuMnhiN48NKVM+OJaR4IkpNTfIPsvm3uUdQThL4ce523QKCLe/97rkCHaAUx6N9+Z6OsLy88qXw2o9L4Z0mLUpf0UrXIPxkrTDLZituAKuS24zeQkP4VPFeXJPfdwZ1jjxjeohvAF50+57OeuHXySLEzDNq/Osc8W0WTn+BZyRYXO32rGcNg2Y4D3AmZiTB+a+Uej1xIhxP1wCHrFt6lWU/AUAAAAASUVORK5CYII=>

[image50]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAWCAYAAAChWZ5EAAABvUlEQVR4Xu2UPyjFURTHj/8WDAxiYEBRBmVQIiFFIWQwGGQwMolBkmJQkhQjyoqUUhb/SpFSykCY/JsVg4Hv1zn3vft+PY+N4X3qM5xzz7vv3vu754rEifNPSIBDcNvcgGuw0Kv5jjy4Cg/hmTkMk72aTDgPl8xJOA5TXcEEHBRdCCVV8NiLo5EON2G2xY3mO5xyRWARTnsx4UK3XHAKW8JjIe4lPHk0OuA1rAnkeYKvMMti/tkHTDNdDXNfcBdXsMsk1aInEAvulpN0B/Irli+0uBn2hUYVbvrWBRXwUfRHdAcewXxX8EuSzBt4BxMjh0N0in6mJpfghVmAJyYX8QbbXcEvGTCjnUqB6L2gL6L3IsMN/vkC2EYjLgANop+Aiyj38rEoFf2MlJczFmzdS9HWlWL4AFP8CtHevRDt6Z/IEa11bRikTLRlfUbFuqAOnkcMhZmF/cFkAD4mu7AtkJ+DuaItyj9ip/nw3flaAPvyALZGDGsH7ImeBKmE+2at5ciy6ORjAXmXSJHojXftTdyin/zEuOhzSddFJ+a3ctRLuE17LNfr5YJyUw6+AzOizzt9Fl1AiVcTJ87f8AmapGz0xTiQaQAAAABJRU5ErkJggg==>

[image51]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABIAAAAWCAYAAADNX8xBAAABJUlEQVR4Xu3TvyuFURzH8W8x+VGSUgZJySQGkl35I6g7kNGuGJQUA4MyGWQwySpkIkUymFhs7Ehi4f19zufpfu/jGXWn+6nX7Z7vOee555znXLNG6p5WbGJPFrGB9uqQLKM4kjtcohIHbGMrFsgJLtCsdj8O0CSeBfxgVm27VqFLPLuqjai9bmkFvZLnEU95Ywrz1b4sx3hHm9pL+MSg5LnBd2jXZBJfmCl2FNJt6SHnsdiDFXm1dB6dcUBJdvCB8Vj8twfFdOAW9/peFt/+M8Zi0Q+vJRbInKW3tlqoD8sDBmLHhKUJp7FIplWP98u37yt1Q6F+6B999vcN+YXzzjdLv+7x2++v2s/FLQdnGpPtdw378oIrS3+JPD7ZV1jG5zRSr/wC4G9EkCWtpNUAAAAASUVORK5CYII=>

[image52]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAWCAYAAAChWZ5EAAABv0lEQVR4Xu3UTShmYRQH8GMUI0IpsmJY+VhYYCULFCspixkbTSP52MhHkVJEkUTyUbaKnSQbgzIG2dpJLGykUMpG0yT+557zdI/rvbJ7Ld5//eo+5z7ve5+Pex+iWGL5RPkGi+ov7EDLqx6R8x0aINPU6qDDtBNgArbVKSxAluuQDXcwqjid8AhfXaeQbMJzwDHJf7rMQ5lp58I57LvCFFzCF8XphxtI1XZYeAAj0Av1KtHcz4AHaDU1Tg/JYCkOrmD21e2PZwOSgkUTHsAtzAXqvL3eAIr0gveIB8FmYAsKXe93sg5dMAC7apL8lQzLMukAavTiAlIU5wdcQ7q2wzJG/v7yy8bOSCYRlmKSZ3qrHvUBVGhj2vZAyrXeFqh/JEvwj95+QcnqhGTL+f2jfJIH9fn9vJRo3X2WkVIAqyQzsuHJ8G9zTI0ftqYGTd0LL/9woOZWwB4owfwk6VMbqK+QvPn2RRwnmTVzaXQX7bAH8YrTTXJYuBOulOTgYJVa4xn+Idl3Dn817J7kIHNpJln2oYDfpo/3Mh0qPob5u00z96tIZsuaTL0aDkgmcKR+mft58J/831pPpl8ssUQnL7oLazXjlUwEAAAAAElFTkSuQmCC>

[image53]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAWCAYAAAChWZ5EAAABXUlEQVR4Xu3UvytGYRQH8KP82LwDGTBYjG9SBlESJiXDa5FRJAuTLMg/IMmqpKxYRCkhpSgpGzNGo5Hvuc95es99eu9z7qAY7rc+9d5zzz3v6b7vvURFivyT1MEynIpjOIQu1ZMnneIT6lXdnL8JS9LIOP1wp47zxH/BNzSoemx+kgcY9wcqb9ASFjMyBY+CF9B3IDY/yQm8QEVwBkltaKQEF7AgwgXM+b3wQe5Cdg630OEbjOzAAMyL8Ccw5/O2u3AvuOkLJn1DJD2wJ5+zFjDnmw2R/MoCB7DqD5BRcreIm8qqXitn0CqfsxaIzadueKf0BZxmeIaVoK4zA4vquNYC1nwahqfUqWq2YDYsqmzDOqwJ/R7YgDGy51MT3MBE+lzyD70itymnD67FkNTC8DJMP4bW/CSN5Dbmx4kdwT60+wZkhKqP0bSqc9rIvQdeBfdcwpyczzO/SJG/yQ8WCm8H14UwlgAAAABJRU5ErkJggg==>

[image54]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACkAAAAWCAYAAABdTLWOAAACDElEQVR4Xu2VP0hWURjGjyVBlFj+QWoQxWgoG2xxcXTQgoammmwIc9CIoHAQh0rBQCWCwKkpxCja/FNBmNDaEphgCUZEBQ0JDi32PJ7njfc73O8mOAn3B7+P75z3PPee++ecG0JBQcGuaIKP5Fv4Cvb6AeC2nIZD8CFsLBlRHp/Ly16Vs/A1fGGFevgDjkhyDf6B1Wpfgi/lYfXdh19gndrlsKzlSFb2LvwkT8BKuGbFMbgO90lyE/6CNWpPwC15Tn3X1b6sdjksazmSZnmjNmCfJAfhN/6pgF9DvP15nIKDkmHCu8ETsZaHZS1H0iwnxnaDLIGDWOTdfCAn4QJsdeNS+Dh4laNp4T8wl5V9AjfhFTkOn8N7LHaGOMlVWCXJRfgd1qrtGYYr8B1sTmp5WC4r+ybENXBLGu/5sycm2RHiJPmIPW3qH0j6Da68pyHuCieTWh7MZWXnQjwfF6otVvKMPy0q+tkTvo/s5wtOjoW4Xfgtoz3EMTOuLwvLetLs4xBXdwr31m34qO+4Ajkb4kFuwAMhHuC3NM5oDDfecvisJ832qM3x1ODi2YZflkW4XxI+5s/weIh753KI25TfqnhhPPAFtY/IedivPp/1pNlD8CPsloSbP+fwDy71JclPIg/KExqnNYby/f0Q4gI478YclT/hlOu3rOWysoTrwL5qnAPtKhlRUFCwM/4CzuKQ7i6ZME8AAAAASUVORK5CYII=>

[image55]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACkAAAAWCAYAAABdTLWOAAACUElEQVR4Xu2VS0gWURTHT9FbFxZFJCgG4sIICorchTt7qJsW1aaCgoioFhUSGpEiJGRQLcoWUSBR9Nr0LnpALXrQg6B3CVJBLQKDgjb1/3/nf/PO+E1Gu2B+8JO5957POXPm3jNmOTk5/8wIuBGek2dgL6yOg8AaeRq+hqfg3ERENlvhMdgq98HKRISzWp6HV81zKbADbjJPlpI58AEcqfFy8wehZBw8C7/ACs1lsRRehqXRXBfsh5OjuXb4RrJAo+C7sHgPLg6DiD5Yruu78KAMzII/4a5orhjd5nELo7kNmlum8RT4Fa6VZDz8qOtCRV7CJZLUmScfYOmfyFDtKvMbHdU4i1rYYn7TACvJ33KNMDGOp8ohzIYfzIPoJXjbhn+Nq8zj16UX/gBfI2WFOqN5noFvcKXcbb7nO0IA3/1+eF/yxt9tsKrFGAtfmVe7JLWWxXb4Qt6B06O16/AH3CIDD8PFf5HkEbgtWqiHt8x/xK1QjB54DU5MLwwDC0JPwE+wRvMXzIszSQZO8g/3x3s4OlogbBePLJl8gCeT/XRMeiGDaZZsNWSeeVLHNT5sfrrTsLfafPg4tRBga4kPBVsIZQUnaK4MHvodMRQ+CG8+kJqfaZ4kmzZZoTHj44fn4SnsrZuwOVog7I83bPB1zjBvrJRNt00egJsVw4TpRbhec/wYPDP/wsTsNE+qSWPu6+dwgSR8m291Xcicn6q9ktlzn8afLf4D/tNiNiqGD0Q/W7Lp8wHZSvbAp5KHZ1EUQ7j/+WWiV2RDIiInJ+fv+AWP2Y+MR7qw8QAAAABJRU5ErkJggg==>

[image56]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACYAAAAYCAYAAACWTY9zAAACYklEQVR4Xu2VS4iPYRTGj2tuiaYRklJCSkyawhC5LFwXshEblKXFpKmhTDEThgWSS1EsXEJSLrklRaFkwQJZKsJashDP4zzf/zv/d94xkyLl/9Sv3nPe833veW/nNfvPtA4cBgtFThNBS+r8k1oLToN+4LboAMNCzCrwHswJvqz6gG3gNXggroKxMQiaDO6Ap4HNVRFmD8FStZeLI+AoaAMHwA3zFe1R28ErUB98O8HdYLPvLWhOfJ+s3C5O8AuYLXuC2CebYsw5MDz4shoNvoFdiX8a+A5myuZMaQ+oRLjOg8vB/gya1B4v9pbdPye2Jtjd6p9NbJH5gK2JnwlH/z3wteyuiGeF29df9iOwUu35YpPsSeCC2j1qgeUTGyf/Idk89LnEjpnHjZK9wfwM8VZeFCPVd938v70SP+Ly70n888wHPCN7t+yhlQjXTfmnBh//xZtYrBi1EWxReww4CHaYr3Sx2l3UZn4r64Jvv/mAXBGKN/CDlT+neOPemcf9aiV4LDgBriKTeAammB8jnu30fFfEK8xZXjFPiLBQckDWt0K8ELfMZ0s6zesTt7hviEt11spLxBr3JPSxppFeq8E8sWIrutMl8+qe0zIRiylrJs9roZMiW9dOmFf6KL5jL4M93Xzb4ts32PxpWR98hYaAx2JE8G+16sSOi2xi983fN4orRT6CxUUAtMS8yjeabxvhTK9Z19pGtYPVImqFVW8lt5lkNRc8N5/JG8GDGcVDy4vAn74QTGxQDJJmgVOpU+Iq81sWXo7LB578FXFr47ubaoZ5rWO5GChqqqmmmn5HPwC8V4VMTqbJfwAAAABJRU5ErkJggg==>

[image57]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACYAAAAYCAYAAACWTY9zAAACUElEQVR4Xu2VS0hVURSGlxSBEVGIYNGDQNKJaDTpJUU26WGDcBI6Mcc2iBBSKOgBSkIPogwKapBCIUhhiDq4aVFBONDAIhAHQdBIggqRqP9nra3r7ntuVxxI0P3gg33W2efedfbZa22R/4x6eAseNJMohS1xcKnshKvjYMRJ+BCugIPmFbjGzTkOv8A9LpZIAWyFH+Go+Qxu9JPAVzgH35pDMAXL3JyX8LCNj5q34R14AV6Hz0VXNCdt8AMsdrGLcNhdk8/wN3xv3pD0Z/iCP+Fuu95mXp2foXN64FoXS6QE/oKXoniFaBL8fAGuZC6+w7023mJ2LNyWM7DOXWfln02sRjSBc1GcCcfxF26cjdew1sb7zSa73g4f2zgnByQzAbLJ4jddjBv+Guw3WVnN7j5pFN1DrMon5nq7x2f4u4uCD3H526N4tWhij1xsStJLfDOcFa08D3+LlRhWjJyCp228QbRwzsOVZiIsY1ZlkYt1iibW5WLcLzEpOBIHI7gtBkRXkUmMwXLRbcS9He/veVjCfMs+0YQoGyUTY3/7G72ivS3rW4NuWSgi9jhuiQB7Gl00O0QTC5/iLJyGW8ME4yn8IcmJHTF9M2XPZGMO3DcT+9o90U7v4Tk26a7ZsWckM7F3osdODI+uN+Y6F+cL+sTumomJpUTPN8KVojx+DoUJoFIyjxGu5je7F3MZnjA9xyT9U/Iz00T2wXHRN/lkcmPGcN+9Eu1nQd+AA7vggzhoFMIJ0ULi//KAp8tCg6SfoTFVor2O7WKVmSdPnjxL4Q+Pi36BFUxEWwAAAABJRU5ErkJggg==>

[image58]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABoAAAAZCAYAAAAv3j5gAAABSUlEQVR4Xu3UvStFYRwH8K+3gbxlUWxmE4WYTMoil0UWKaUYzTZlkl1GRspLsZCYKMSkxH9gMYvvz+973PN2r3OlO51vfYbze557fud5zn0OkOefU0NnNBUfKJElOqR92qBW+TVVa7RIn8jWaIG2qV7XE3QsJdMt58je6JL6YrUH6YnVf7Inw/BGhehwai7oiNp03Ugv0hJMCseefkW6kH1FM/C5rzQKf09WM4k00wnVSSWNLMvw+eYWvrpghZFsIrrPlTQaoWuapDv4706lNjQPQ7QeLiB7IzsGz9Sr63b41gWrm1X9O1VrtBYaSPNUnJrIAN3Hiyj+e+3wlo3dIG1F8dPej/QHWRU7+GUzCG80HaqN0xvNicW27gq+Kw2qdcIPvGlSLZEtuYE3eqcdjY3RB81LkA46oEf4+9mFfxFKfhXy5Mnzt3wBL9BVxL+EBosAAAAASUVORK5CYII=>

[image59]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAB8AAAAZCAYAAADJ9/UkAAAB40lEQVR4Xu2UPUiWURTHTx8mWeDQZsGbFNEQghISaUMOtZUQ1BThHEQOguauVhoOiYNSQ2CD2AcIgloplCh9QCQNUeAguIRuhS71/3fO5Tn3PphBwzv4/uA33HMPz7n3PudekRJbsw/WmjuTuf9mN7xlvoYT8JqbPw1/mWvwBXwFB1xOoFr0G3OiOSfi6TxFLf5YsuLkEvwBy23cCH+aG6LFr9ucZw/8BJttfAwuw6Nmjhb4Fe4wSSdcgRU2boDd5t+4CpeS2BPYb+b4CO+lwYRT8m/FR+GbJMZf896MKIj+xx74yHwHZ+CRLO1P8TFzBM7Dt/C4yyGMTycxbmzVjDgjWvyz6BGHY74NFyS7VidFT4jy2pEOuCjarAGOp9yY3JWsWX2unLNgrw+CJouft/EueNAM1IjmXHYxHm1a/I5kxcv8RJ0Fb/qg6E4Zb0vinirJL5yFeRM8ffC7GVHU4vvhOmxN4qF4u42fw3EzcEiyZg3cF206D7t91swxKfEHSPjnbEjCRuKO/K7qRXMuuNgV+M2NyTPYZeY4K/oqsRMpH5qHEu/yBrxoBoYlziGVogvl4klB9NHhE7vpM8sV83/RL6KncSDKEBk0X8IPcAjujTKUw/ABfCp6NcONKVGixDbjNzgtgxlh+ccrAAAAAElFTkSuQmCC>

[image60]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADYAAAAZCAYAAAB6v90+AAADAklEQVR4Xu2WWahOURTHFzKF0EXGB/N9I2PycM2UkBIP3DKnKBmLyJAhITJH3AeKyPBgjIwZEoVIpHgRDwpJisT/31r7fuvuzne+zwv6Or/61dlr73u/s87ee+0tkvFXqA83wrWwY9TnmQIr4uC/og9sGAcj9sNK2Bq+hhPM2tbPv18FX9pzQWrBFfCFeRuegq38INAZHjLPwqNwVI0R+fkIf8B78DK8avJ/kjL4TXTWyE642NwHV4r+7mM4xMYUpGQTY1LPYQuTbIXnqkeI1IMPRJcUJXyJK3BwGJTCe/gLPoHbRBOhgUHws2vPgUPNAPfdXtdOpS38Kbp2Pf1FX6SbtUeIzmLMeHgkDiZwKw5EDIBfXHum6MyE2eGqOiM1P0Yqw0UTWBLFO1l8rrU57jscawYWwTWunY/rcSCiqejvNbL2etjeJPPgNHsuCi6jpMQ4U4xvsDar0F2L0d2iyd4QfalC3Ic74AX4Fs42PVVwlujePubiTI57+o9oDr/CdVE8zCQ3boAJhAITEpzu+tN4A/vZcxfR5U/9Hmomuqw3iZb8AJPsbs8V8ACclOvODw/Ep6JJUsKvyxffYu268LDoB6DLrJ8OszFpdIjaLETUF6iYcSYrIukluqT5LlwxvS2eF27MzaKbk7Ii8nTnS8+3MdzMfnmQ0aLV7lUUL4aLJo+BJJrAa2YDi+2By+2ZxwTfM5WSTSyJgaKJcfoJE56Y666mXHRcm7jDsVT0iuSXI88/+sHFPLvgGDPAwz18aE7GCdeXSBU8HcVWw4euzTNsqmsH6ohWuXCfY7uxGdguOjOhdBNeCGjS2dgXnoyDojeVkBg57p4TuQkPujYP53eisxbgsnsmumH9puUP8doTOC86jobrUU/RGQiMhJ/Mri5OOBOXYLsoTnjr4C2JtBS9waTCEso7GO9wlOWcsRjevB+ZXPtcCgslN1uEXzUcCbyGBSbDO6JVjWdfDzOGy5Zjk+BVjsuX/5fVumBV/J9YEAciZohehos6xzIyMjIySprf4lm9qDR6WLcAAAAASUVORK5CYII=>

[image61]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADYAAAAZCAYAAAB6v90+AAADEUlEQVR4Xu2WWahOURTHl5kQMg8vKJQ3QxK5ZkqmEg/INZUiMobIkCEh85DpPhAyP6BExgyZMiZSnkR5MSSlxP/fWvt++657vuFJt6/zq1+dvfb+zvnW2Wvvs0VS/gt14Ea4FrZ3fTGTYIkPVmUOwMmwFfwAx5nVrb8eXAXf2XVeqsEV8K15F56DLeJBoCM8Yl6EJ+DwCiOy0w7ehg/hPdjPDDSFv0RnjeyCi8z9cKXoc5/DgTYmL0WbGJN6A5uZZCu8VD5CpDZ8DHuYhH/iGhwQBmWhJnwKS63dRrTUaF+L9Yff7JrMgoPMANfdvqidEz7kj2jtxvSCf2Enaw8VnUXPWHjMBx0T4BfRygjsMDnzpDf8kemWGaIzE2aHv70gOrMFMUQ0gcUu3sHis63Ncb/hKDOwEK6J2kkch89cbKn5HdaAjUSfV9/614uWLyVz4FS7LgiWUVJinCnGN1ibu9B9i9E9osneEv1Tubgjuq5i5pq8V2uLlcGZomv7pMUIkwszWzBN4E+4zsXDTHLhBphA2GBCgtOi/my8kMqJcQYo79HVYo1Fy3qT6JYfYJKd7boEHhQt77zwg/hKNElKdoo+dIu1a8Gjoi+ALrN+OtjGZOORVE6MJU7jxDyjTe6IpBu8KfpfWDHdLZ4VLszNoouTckfk150PnWdjuJjj8iAj4Gf43sU9V+ADF+N9KZ/R0vWRhvCGWddie+Fyu+anh/8zJ0WbWBJ9RB/K6SdMeHymu5wuUnEDSGI7fOliLGX6ycUDu+FIM8CXE140J+N01JdIGTzvYqvhk6jNb1hp1A5wq/4omfMc2w3MwBj4NWoTniyorwLSE571QXBdMomRU9F1IjzqHI7a/DjzTXLWAiy716ILNl60fBCPPYHLouNoOB4xSZ48uBGQ5qIHWTrMYgHOBEu3rYsTnjp4SiK8x7aoLxFuoTyDXTW5nTPm4cmbH1rK2mcpLJDMbBG+1fBJ4DEswFI9BM+I/n6K6VkCJ/qgwaMcj3C8L3frvLtiVWK+Dzimix6GC/qOpaSkpKQUNf8A66e/tIBzj/YAAAAASUVORK5CYII=>

[image62]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABUAAAAZCAYAAADe1WXtAAABDUlEQVR4Xu2TvWoCQRSFB4ToAxiwEPMIgp3dvkB8gVSptUgXBRGxM6WkSxEsTZlWxEIkhY/g3zYWgmBtpecyV5256w5baGHYDz6YPTN7dpbZVeq/koNPMoxCCf7JkKnDPfRhH47gM+vkaqVdpRcdF07t6RMNuIMb+AOL9nQ4bTiXIUOlngyj4Cql1/dkGAVXaQ124C9cwi+YYJ1Q6UyGTBV+8vgBjmGLdeLaaRqmjOsm3LJJIw9ApQsZhlBR+hMjC2LO4maldAgmGZYe9mbkND6W5o08wKXSLEs3vxv5B1yzdHChUKkvQ+Zb6XKCDo3+vBc2QFmdf9OV0jsawp65CDwqvWYAJ/DVno6JuR8OBXlCCc/N8p0AAAAASUVORK5CYII=>

[image63]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABUAAAAZCAYAAADe1WXtAAABKklEQVR4Xu3TP0tCURgG8CeEanAsaBAjv0DQVtP9AvkBDIe2Bocm/0BFtNXgEEFDQns0iZs0RVOObUG1BkGzkz1v73vleDxeXRwUH/jBve855/UcDxeY12Rp0y9OmjS905ZXP6EefVGbnmnfjM1Umtahi3Ne/Yy69EMPtDs4PDo71IE29XcqTSOvlpgl06I8wk3l+JFXS8yRKUAXho5fo2tq0ifdUcoMZQ36HwlJhHDTKt3Y8zK90IUZyi30qPFxI4Sbyo+vOu/n9GtWnDr26NQtYHRTPyXoPCEX3M9Uml46AyEN2jAfdKzL/iPP8bxtpx7MAQZ3mjFSq8STmCv6NnJxiSkifPx7aHOJXJp8yrIBkZhHeoM2lR2UnbF16Df/RK906IwtsshM5Q9QAEuuQDY/+wAAAABJRU5ErkJggg==>

[image64]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACoAAAAZCAYAAABHLbxYAAABMUlEQVR4Xu2VPUoEQRCFC/FvEwN/MDBxRUNBvIGhsvGCgZhsYqaJiWCigZoY6wEMxVAxMfQAG3uCvYLo6+1qeRSsXS0OKPQHX9BV8+iamR5GpFIZsqX24bjp5eBcabaYPz/oLXyBj+qH+DfjbMp5sz/mSA0bTpheDs6VZotpctBFuGmLxBTs2OIomhy0BR/gmsqMwXuJ59zFoVpyRhOcG5Wdh0/qEtWv4S6tszT5RBPL6rPEYS/hAfVd8KCTppeDc55sG77BU9vw8C8HDV9hCZzzZM/ghcQjsGB6WXKDztgC4R30RD3W9arEn8Xs1xUOeNBp09uBA7inWjhns4kuPFeZFXgn39/gkJ7EVxDOTDBs+Kq1Ob1mG77DfTXB2ZSz2cA6vKG1ZQNe2WKlUqlUfodPtw9OcyLL+CkAAAAASUVORK5CYII=>

[image65]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADYAAAAZCAYAAAB6v90+AAACsUlEQVR4Xu2XSahPcRTHDzKF0EMyLMxLL8+QLEzJSjbKAgsZUtRLvWchLzImY+YIGwuRYWHMTCSxIBIbNoaFQpKFxPfbOT/OO93/cDfo3/3Up+49v9//3XvubzpPpOCv0BFugmvhoNDmmQsnxuC/YjTsHIOBg3Ae7AtfwVlmW2vn71fDl3ZdkTZwFXxh3oWnYR/fyehuroPbQls5PsLv8D68Aq+bQ6y9Dn4THTWyGzaZB2ALPAIfwynWpyI1mxiTeg57mYQvff53D5EB8D08bH6yPtXC3/6ET+AO0URoYhL87O6XwKlmgutuv7svSz/4Q3TuesaJvsjwEE+8lXyJ3YmBwHj4xd0vFB2ZNDqcVWel9ccoyzTRBJpDfLDFl4Z4Im9iN2MgwOnN53Wx+w2is4SSZXC+XVfFZMlOjCPF+MYQT+RN7AHcBS/CN3Cx6TkKF4mu7eMuzuTOufuq6Am/wvUhnkaSCzcLvlyexF7DsXY9VHT6U7+GesBjcLPolp9gkiPsmufXITj7T3NpeCA+FU2SEn5dJrY1dQrkHbGB4f6h6TeoyEyTOyIZJTql28O9sMHiJeHC3CK6OClfmKc7E2t0/TxMbHsM5uCSyWMgi27whtnJYvvgSrvmMVHxw9ZsYllMEE2Mw59FnsRWiJZIfjpeNT+4mGcPnGEmeLinD83BOOnaMuFudCbE1sBHIeYplVg72NVM7BQdmbR1ExYElBVOZAw8FYOilYqfQSfcdSa3RauJBA/nd6KjVgomxgoicgE+M1N5VC86AonpopULHebihCNxGfYPccKqg1US6S3Zz28Ft1DWYKzhKOtFxjwcCbZdMzlNOY0YSw8j/Kqp5uzg4nPgPdFd7RYcaUY4bdk3C/6HwOnLv8vduuKu+D+xPAYCC0SL4arOsYKCgoKCmuYXraes5v9jnwIAAAAASUVORK5CYII=>