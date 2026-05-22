# Yuxi-RAG 实验评估报告

## 1. 运行信息
- run_name: `yuxi_rag_eval_20260522_144127`
- total_questions: 2
- top_k: 5
- retrieval_only: false
- skip_ragas: true
- generated_at: 2026-05-22T14:41:31Z

## 2. 总体指标
- Hit@K: 1.0000
- Recall@K: 1.0000
- MRR: 1.0000
- Faithfulness: N/A
- Answer Relevancy: N/A
- Context Precision: N/A
- Context Recall: N/A
- Answer Correctness: N/A

## 3. 每个问题结果

### q001 - RAG 是什么？

- question: RAG 是什么？
- ground_truth: RAG 是检索增强生成，会先从外部知识库检索相关文档片段，再把这些上下文交给大模型生成答案。
- answer: 根据提供的资料，RAG（Retrieval-Augmented Generation，检索增强生成）是一种把大语言模型内部知识与外部知识库内容结合起来的技术范式。它会在模型回答之前，先从知识库中检索与问题相关的文档片段，再把这些片段作为上下文交给大模型生成答案。

来源：01_RAG_intro.md，chunk=0
- sources: `01_RAG_intro.md`
- expected_source_hit: True
- keyword_hit: True
- rank: 1
- metrics:
  - hit_at_k: 1.0000
  - recall_at_k: 1.0000
  - mrr: 1.0000
  - faithfulness: N/A
  - answer_relevancy: N/A
  - context_precision: N/A
  - context_recall: N/A
  - answer_correctness: N/A
- error: None

### q002 - 为什么 RAG 需要优化分块策略？

- question: 为什么 RAG 需要优化分块策略？
- ground_truth: 分块策略影响检索质量，过短会切碎信息，过长会引入无关内容，段落优先分块能更好保留语义边界。
- answer: 根据现有资料，RAG 需要优化分块策略是因为分块策略会直接影响检索质量：如果 chunk 太短，信息可能被切碎；如果 chunk 太长，检索结果可能包含太多无关内容。段落优先分块会尽量保留自然语义边界，再用 chunk_size 和 chunk_overlap 控制长度。[Source: 01_RAG_intro.md, chunk=0]
- sources: `01_RAG_intro.md`
- expected_source_hit: True
- keyword_hit: True
- rank: 1
- metrics:
  - hit_at_k: 1.0000
  - recall_at_k: 1.0000
  - mrr: 1.0000
  - faithfulness: N/A
  - answer_relevancy: N/A
  - context_precision: N/A
  - context_recall: N/A
  - answer_correctness: N/A
- error: None

## 4. 自动诊断

- 当前设置了 --skip-ragas：只输出基础检索指标和问答结果。
