# Experiment Report / 実験設計と結果

## 1. Research question

日本語の専門教材QAにおいて、細粒度のGraph Keyを使いながら、Solverが読む根拠を原文Chunkだけに限定すると、回答Accuracyと根拠監査性を両立できるかを検証しました。

## 2. Evaluation setting

| Item | Setting |
|---|---|
| Benchmark | 人工確認済み日本語QA 229問 |
| Split | Development 160 / Validation 69 |
| LLM | qwen3:14b |
| Embedding | bge-m3:latest |
| Main metric | Official answer accuracy |
| Grounding metric | Source-only evidence term recall |
| Runtime metric | End-to-end mean / P50 / P95 latency |
| Retrieval budget | Source 32、各Key 16、最終Top-8 |

Splitはexam、chapter、subject、sourceを使ったdeterministic stratificationで固定しました。DevelopmentとValidationのIDは重複せず、Candidateは事前登録した順序でGate評価しています。

## 3. Graph construction

Grounded KV3は以下のKey/Valueを構築しました。

| Component | Count | Role |
|---|---:|---|
| Source Value | 378 | Solverへ渡す400/50原文Chunk |
| Sentence Key | 2,508 | 文単位の位置特定 |
| Verified Fact Key | 1,190 | 原子Factによる位置特定 |
| Canonical Entity | 1,807 | 表記統合とPath endpoint |
| Strict Path Key | 149 | 条件付きmulti-source接続 |

Fact候補2,170件は原文quoteのみでentailment確認し、1,190件を採用、980件を除外しました。FactとPathのsource quoteは、正規化後に原文Sourceへ投影できることを構築条件にしています。

### Graph scale

| Graph | Nodes | Edges | Searchable keys/chunks | Edge/Node |
|---|---:|---:|---:|---:|
| Old KAG official graph | 6,726 | 12,483 | 378 | 1.86 |
| Grounded KV3 | 7,371 | 5,422 | 4,225 | 0.74 |
| LightRAG all-book | 3,184 | 7,359 | 638 | 2.31 |

Label定義が異なるため絶対数は直接比較できません。KV3の低いEdge/Nodeは、弱いco-occurrenceを追加せず、原文provenanceを優先した疎な設計を示します。

## 4. Candidate protocol

候補は次の順番で事前登録しました。

1. `kv_source_projection`
2. `kv_conditional_path`
3. `kv_entity_passage_ppr`
4. `kv_contrastive_verifier`
5. Overfetch/PPR/context-order backups

各候補はDevelopment、Full benchmark、Finalizerの順でGateを通過する必要があります。成功候補が出た時点で探索を停止し、Validation結果を見ながら後続方式を追加選択しない設計です。

### Gate result

| Candidate | Dev Accuracy / Evidence | Full Accuracy / Evidence | Legacy | Guarded | Status |
|---|---:|---:|---:|---:|---|
| Source Projection | 0.894 / 0.723 | 0.865 / 0.727 | 198 | 200 | Rejected |
| Conditional Path | 0.912 / 0.725 | 0.878 / 0.727 | 203 | 203 | Selected |

Source ProjectionはLegacy 198で事前閾値199に届かなかったため、Guarded 200だけを理由に採用しませんでした。Conditional Pathが全Gateを通過したため、PPRとVerifierは正式なFull runを行っていません。

## 5. Final result

| System | Correct | Accuracy | Answer recall | Evidence recall | Mean / P95 latency |
|---|---:|---:|---:|---:|---:|
| KV3 / Off | 201/229 | 0.878 | 0.812 | 0.727 | 5.21 / 6.12s |
| KV3 / Legacy | 203/229 | 0.886 | 0.696 | 0.727 | 10.11 / 12.17s |
| KV3 / Guarded | 203/229 | 0.886 | 0.812 | 0.727 | 15.04 / 18.57s |

Off、Legacy、Guardedは同じretrieval evidenceを利用しており、Evidence mismatchは0件でした。Legacyは198問へ適用し31問でOffへfallback、Guardedは2問だけoverrideし227問でOffを維持しました。

Candidate poolには平均48.98件のValueがあり、Evidence Recallは0.905でした。Top-8では0.727となり、約0.178の差があります。これは構図の生成よりもSource rerankingに改善余地があることを示します。

## 6. Interpretation

### What improved

- Fine-grained Keyで直接因果を含む原文を上位化できた。
- OffだけでLightRAGのAccuracyを数値上上回った。
- Pathを固定quotaにせず、厳しいGateで少数使用した。
- Keyが生成情報でも、Solver入力を原文Valueへ限定できた。

### What did not improve

- Evidence RecallはLightRAGの0.840に届かなかった。
- 疎なGraphは条件、手順、比較などのmulti-hop contextを失う場合がある。
- Guarded Finalizerは変更が少ない一方、追加推論のLatencyが大きい。
- Private benchmarkのため、公開Demoだけでは研究値を完全再現できない。

## 7. References

- [OpenSPG KAG repository](https://github.com/OpenSPG/KAG)
- [KAG: Boosting LLMs in Professional Domains via Knowledge Augmented Generation](https://arxiv.org/abs/2409.13731)
- [LightRAG repository](https://github.com/HKUDS/LightRAG)
- [KG2RAG: Knowledge Graph-Guided Retrieval Augmented Generation](https://aclanthology.org/2025.naacl-long.449/)
- [HippoRAG](https://proceedings.neurips.cc/paper_files/paper/2024/hash/6ddc001d07ca4f319af96a3024f6dbd1-Abstract-Conference.html)
- [KiRAG](https://aclanthology.org/2025.acl-long.929/)
