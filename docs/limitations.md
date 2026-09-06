# Limitations and Next Steps

## 1. Evidence Recall gap

最終Accuracyは0.878/0.886でしたが、Evidence Recall 0.727はLightRAG 0.840より低いままです。Accuracy改善をGrounding全体の優越と解釈できません。

次はCandidate pool 0.905からTop-8 0.727へ落ちる区間を対象に、Source reranker、query-dependent budget、cross-encoderのcost/benefitを検証します。

## 2. Sparse graph

Grounded KV3のEdge/Nodeは0.74で、直接QAには高precisionですが、条件、手順、例外、対比を結ぶmulti-hop contextが不足する場合があります。

弱いco-occurrenceを無制限に追加せず、provenance付きの同義語、条件、手順順序、鑑別relationを候補にします。Direct channelとExpansion channelを分離し、拡張edgeがSource Top-8を汚染しない設計が必要です。

## 3. Comparison constraints

- 同じ229問でもGraph、Chunk representation、Finalizer条件は完全には同じではありません。
- LightRAGとのpaired significance testは未実施です。
- 一つの専門領域と選択式QAが中心で、一般QAへの外的妥当性は未確認です。
- ModelとEmbeddingを固定しているため、別modelで同じ傾向になる保証はありません。

## 4. Reproducibility boundary

研究用benchmarkは公開できないため、公開リポジトリはfull experiment reproductionではありません。合成Demoはroute merge、Path gate、projection、MMR、source-only outputを検証するためのものです。

## 5. Production concerns

公開実装はretrieval algorithmのshowcaseであり、次のproduction機能はscope外です。

- Distributed index refreshとzero-downtime reindex。
- Embedding modelのversion migration。
- Per-tenant authorization。
- Online evaluation、drift detection、cost budget。
- Neo4j outage時のfull fallback policy。
