# Day 14 — Exercises

## AI Evaluation & Benchmarking · Lab Worksheet

**Thời gian làm bài:** 09:15–12:00

**Domain:** Northstar University Student Services

Điền trực tiếp câu trả lời vào file này. Golden dataset 20 QA được viết một lần
duy nhất trong `golden_dataset.json`, không chép lại toàn bộ vào Markdown.

---

Từ 09:15–09:30, cài môi trường và chạy baseline tests theo `guide_lab.md`.

---

## Part 1 — Warm-up (09:30–09:45)

### Exercise 1.1 — RAGAS Metric Thresholds

Theo bài giảng:

- 0.8–1.0: Good — monitor, maintain.
- 0.6–0.8: Needs work — analyze failures, iterate.
- Dưới 0.6: Significant issues — investigate.

Với từng metric, xác định khi nào score thấp có thể chấp nhận và khi nào là
critical.

| Metric | Acceptable Low Score Scenario | Critical Low Score Scenario | Action Required |
|---|---|---|---|
| Faithfulness | A short, clearly labelled refusal for an out-of-scope or evidence-free request may have low lexical grounding but is still safe. | A student-services answer introduces unsupported dates, fees, eligibility, or private-data claims. | Block unsafe factual answers; inspect retrieved evidence and add grounding checks. |
| Answer Relevance | A deliberately narrow clarification can score low when the question is genuinely ambiguous. | The answer addresses a different policy or ignores the student's requested action. | Improve intent routing and require the answer to address every requested part. |
| Context Recall | A non-answerable/out-of-scope request need not retrieve policy evidence beyond the scope rule. | Required policy conditions, deadlines, or exceptions are absent from retrieved chunks. | Improve query formulation, chunking, or retrieval coverage. |
| Context Precision | A broad multi-part question may retrieve a small amount of supporting background noise. | Relevant evidence is buried behind unrelated chunks, increasing generator distraction. | Add reranking or source-aware retrieval filtering. |
| Completeness | A concise answer can omit optional detail while retaining all requested requirements. | It omits a required deadline, amount, condition, exception, or next step. | Add completeness checks and few-shot examples for multi-condition answers. |

### Exercise 1.2 — Bias trong LLM-as-a-Judge

Ba bias thường gặp:

- Position bias: judge ưu tiên answer xuất hiện trước.
- Verbosity bias: judge ưu tiên answer dài hơn.
- Self-preference: judge ưu tiên output giống chính model đó.

**Câu 1: Thiết kế experiment phát hiện position bias với ít nhất hai conditions.**

> *Câu trả lời:* Tạo các cặp response A/B có chất lượng cố định và chấm hai conditions: Condition 1 trình bày A trước B; Condition 2 đảo B trước A. Randomize thứ tự trên toàn bộ 20 câu, giữ nguyên prompt/rubric/model, rồi so score của cùng một response giữa hai vị trí. Nếu response ở vị trí đầu nhận điểm cao hơn có hệ thống (ví dụ mean paired delta > 0.10 và lặp lại trên phần lớn cặp), judge có position bias.

**Câu 2: Làm thế nào giảm verbosity bias bằng rubric design?**

> *Câu trả lời:* Rubric chỉ cấp điểm cho required facts, conditions, evidence, safety và actionability; không cấp điểm cho độ dài. Nội dung lặp, ngoài câu hỏi hoặc claim không có evidence không được cộng điểm và có thể bị trừ ở Relevance/Faithfulness. Calibration set cần có cả response ngắn đạt điểm 5 và response dài nhưng nhiều noise đạt điểm thấp.

**Câu 3: Tại sao cần calibrate LLM judge với human labels?**

> *Câu trả lời:* Human labels là chuẩn tham chiếu để kiểm tra judge có hiểu đúng policy, exceptions và safety/privacy hay không. So sánh judge–human giúp phát hiện leniency, severity, position và self-preference bias; từ đó điều chỉnh rubric/threshold trước khi dùng judge làm quality gate.

### Exercise 1.3 — Evaluation trong CI/CD

**Câu 1: Chọn threshold để block deployment.**

| Metric | Threshold | Lý do |
|---|---:|---|
| Faithfulness | 0.80 | Unsupported policy claims can mislead students; block deployment until grounding is restored. |
| Answer Relevance | 0.70 | A response that misses the request creates operational friction and should fail the quality gate. |
| Completeness | 0.75 | Missing conditions, deadlines, or exceptions can cause incorrect student actions. |

**Câu 2: Khi nào dùng offline evaluation, online evaluation và human review?**

> *Câu trả lời:* Chạy offline evaluation trên Golden Dataset sau mỗi thay đổi code, prompt, retriever, model và trước release. Dùng online evaluation sau deploy để theo dõi traffic mẫu, latency, cost, drift và failure mới. Human review bắt buộc cho privacy/safety, appeal, trường hợp score thấp hoặc bất đồng giữa lexical metrics và trace; nhãn human được đưa lại vào bộ calibration/regression.

---

## Part 2 — Core Coding (09:45–10:40)

Hoàn thiện các TODO bắt buộc trong `template.py`.

### Task 1 — Data Models

- `QAPair`: question, expected answer, gold context, metadata và retrieved contexts.
- `EvalResult`: answer-side scores, optional retrieval scores, pass/failure fields.
- `overall_score()`: trung bình Faithfulness, Relevance và Completeness.

### Task 2 — RAGASEvaluator

Answer-side:

- `evaluate_faithfulness(answer, context)`
- `evaluate_relevance(answer, question)`
- `evaluate_completeness(answer, expected)`

Retrieval-side:

- `evaluate_context_recall(contexts, expected)`
- `evaluate_context_precision(contexts, expected)`

Full pipeline:

- `run_full_eval(..., contexts=None)` luôn tính ba answer metrics.
- Nếu có `contexts`, tính và lưu thêm Context Recall và Context Precision.
- Retrieval scores không làm thay đổi `overall_score()` và pass rule gốc.

### Task 3 — LLMJudge

- `score_response(question, answer, rubric)`
- `detect_bias(scores_batch)`

### Task 4 — BenchmarkRunner

- `run(qa_pairs, agent_fn, evaluator)`
- `generate_report(results)`
- `run_regression(new_results, baseline_results)`
- `identify_failures(results, threshold)`

`BenchmarkRunner.run()` phải truyền `pair.retrieved_contexts` vào
`run_full_eval()`. Report phải có average của hai retrieval metrics.

### Task 5 — FailureAnalyzer

- `categorize_failures(failures)`
- `find_root_cause(failure)`
- `generate_improvement_suggestions(failures)`
- `generate_improvement_log(failures, suggestions)`

Kiểm tra:

```bash
pytest tests/ -v
```

**Checkpoint implementation report (Part 2):** Completed all required TODOs in `template.py`: typed data models; five bounded word-overlap metrics; rank-aware Average Precision; optional retrieval-metric wiring; JSON-backed mockable LLM judge; benchmark reporting and regression gate; failure clustering, root-cause mapping, suggestions, and Markdown improvement log. The optional lexical reranker is also implemented. Official execution evidence, 2026-08-12: `.venv\\Scripts\\python.exe -m pytest tests/ -v` completed successfully with **42 passed in 0.06s** under Python 3.12.10. The supplied tests cover metrics, retrieval wiring, runner, judge, regression, failure analysis, and the bonus reranker.

`rerank_by_overlap()` là TODO bonus của Exercise 3.5. Test tương ứng được skip
nếu bạn chưa làm bonus.

---

## Part 3 — Golden Dataset & Real Benchmark (10:40–11:35)

### Exercise 3.1 — Build the Golden Dataset

Thiết kế và validate dataset theo Mục 5–6 trong `guide_lab.md`. Nội dung 20 QA
được điền trực tiếp trong `golden_dataset.json`; phần dưới chỉ ghi lại kết quả
và quyết định thiết kế, không chép lại toàn bộ QA.

**Kết quả dataset**

| Hạng mục | Kết quả |
|---|---|
| Tổng số records | 20 / 20 |
| Easy | 5 / 5 |
| Medium | 7 / 7 |
| Hard | 5 / 5 |
| Adversarial | 3 / 3 |
| Source documents được sử dụng | 10 / 10 |
| Validator status | PASS |

**Ba case đại diện cho quyết định thiết kế**

| ID | Difficulty | Source document(s) | Vì sao case phù hợp với difficulty/attack type? |
|---|---|---|---|
| E03 | Easy | `03_tuition_payment_refund.md` | Factual lookup trực tiếp một khoản phí USD 75 từ một đoạn nguồn. |
| M05 | Medium | `02_course_registration.md`, `03_tuition_payment_refund.md` | Kết hợp approvals, số tiền và thời hạn thanh toán từ hai chính sách. |
| H03 | Hard | `09_privacy_security_and_policy_updates.md`, `02_course_registration.md` | Phải chọn policy version theo event date và không bị đánh lạc hướng bởi cuộc trao đổi trong tháng 7. |

**Điểm khó nhất khi xây dựng expected answer hoặc evidence là gì?**

> *Câu trả lời:* Khó nhất là viết expected answer đủ dates, amounts, conditions và exceptions nhưng vẫn ngắn, đồng thời chọn evidence nguyên văn hỗ trợ từng claim. Review semantic phát hiện H01, A01 và A03 ban đầu thiếu một phần evidence; các contexts đã được bổ sung và validator chạy lại vẫn PASS.

**Xác nhận:**

- [x] Mọi claim trong expected answer đều có evidence hỗ trợ.
- [x] Không có questions trùng ý và không dùng kiến thức ngoài corpus.
- [x] `.venv\Scripts\python.exe validate_golden_dataset.py` báo `PASS`.

### Exercise 3.2 — Benchmark Run

Chạy:

```bash
python domain_assistant.py
python evaluate_answers.py
```

Copy bảng terminal vào đây hoặc điền từ `artifacts/benchmark_results.json`.

| ID | Question (short) | Ctx Recall | Ctx Precision | Faithfulness | Relevance | Completeness | Overall | Passed? | Failure Type |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| E01 | Fall registration close | 1.000 | 1.000 | 1.000 | 0.571 | 1.000 | 0.857 | Yes | - |
| E02 | Waitlist offer time | 0.667 | 1.000 | 0.429 | 0.500 | 0.778 | 0.569 | No | off_topic |
| E03 | Late-payment fee | 1.000 | 1.000 | 0.923 | 0.750 | 0.909 | 0.861 | Yes | - |
| E04 | Merit scholarship proportion | 1.000 | 1.000 | 1.000 | 0.500 | 1.000 | 0.833 | Yes | - |
| E05 | Attendance alert trigger | 0.917 | 0.750 | 0.212 | 0.667 | 0.583 | 0.487 | No | hallucination |
| M01 | Stop attending after census | 1.000 | 1.000 | 0.636 | 0.800 | 0.909 | 0.782 | Yes | - |
| M02 | Internship completion | 1.000 | 0.700 | 0.850 | 0.778 | 1.000 | 0.876 | Yes | - |
| M03 | Service complaint escalation | 0.944 | 0.867 | 0.462 | 0.857 | 1.000 | 0.773 | No | off_topic |
| M04 | Account compromise steps | 1.000 | 0.917 | 0.531 | 0.500 | 1.000 | 0.677 | Yes | - |
| M05 | Late-add requirements | 1.000 | 1.000 | 0.607 | 0.667 | 1.000 | 0.758 | Yes | - |
| M06 | Scholarship renewal failure | 0.938 | 1.000 | 0.577 | 0.625 | 1.000 | 0.734 | Yes | - |
| M07 | Incomplete-grade requirements | 0.895 | 1.000 | 0.400 | 0.600 | 0.895 | 0.632 | No | off_topic |
| H01 | September 1 tuition reversal | 0.867 | 1.000 | 0.583 | 0.727 | 0.667 | 0.659 | Yes | - |
| H02 | Financial hold and graduation | 0.944 | 1.000 | 0.462 | 1.000 | 0.722 | 0.728 | No | off_topic |
| H03 | August 1 late-add version | 0.789 | 1.000 | 0.633 | 0.846 | 0.632 | 0.704 | Yes | - |
| H04 | Travel leave scholarship | 0.941 | 1.000 | 0.933 | 0.818 | 0.824 | 0.858 | Yes | - |
| H05 | Grade-appeal decision | 0.895 | 1.000 | 0.750 | 0.923 | 0.895 | 0.856 | Yes | - |
| A01 | Legal advice request | 0.364 | 1.000 | 0.188 | 0.625 | 0.182 | 0.331 | No | hallucination |
| A02 | Prompt-injection request | 0.895 | 0.887 | 0.889 | 0.600 | 0.474 | 0.654 | No | off_topic |
| A03 | Parent-record premise | 0.917 | 0.950 | 0.960 | 0.455 | 0.917 | 0.777 | No | off_topic |

**Checkpoint report (Exercise 3.1):** The completed `golden_dataset.json` contains 20 records: 5 Easy, 7 Medium, 5 Hard, and 3 Adversarial. It uses all 10 source documents. Official execution evidence, 2026-08-12: `.venv\\Scripts\\python.exe validate_golden_dataset.py` reported **PASS: dataset structure and evidence provenance are valid**, with 20 QA pairs, difficulty counts 5/7/5/3, and document coverage 10/10. Static evidence verification also found 0 verbatim-substring mismatches.

Representative design choices: E03 tests a direct late-payment policy lookup; M05 combines late-add approvals with the payment deadline across two documents; H03 tests event-date policy-version selection; A01/A02/A03 exercise scope refusal, prompt-injection resistance, and false-premise correction. Expected answers are English, concise, and preserve policy conditions, dates, amounts, and exceptions.

**Aggregate Report**

- Overall pass rate: 60.0%
- Avg Context Recall: 0.899
- Avg Context Precision: 0.954
- Avg Faithfulness: 0.651
- Avg Relevance: 0.690
- Avg Completeness: 0.819
- Failure type distribution: `off_topic=6`, `hallucination=2`

**Ba cases có Overall Score thấp nhất**

1. ID: A01 | Score: 0.331 | Failure type: hallucination
2. ID: E05 | Score: 0.487 | Failure type: hallucination
3. ID: E02 | Score: 0.569 | Failure type: off_topic

**Benchmark interpretation:** Context Recall (0.899) and Context Precision (0.954) are strong, while Faithfulness (0.651) is the weakest aggregate metric. This pattern indicates that BM25 thường lấy đúng evidence; phần giảm điểm chủ yếu đến từ answer mở rộng ngoài gold excerpt và hạn chế lexical overlap. Khi tính chẩn đoán Faithfulness trên retrieved contexts thật, trung bình tăng từ 0.651 lên 0.818; vì vậy cần review trace/LLM judge trước khi kết luận hallucination.

**Nhận xét ngắn:** Metric nào yếu nhất? Kết quả gợi ý vấn đề nằm ở retrieval
hay generation?

> *Câu trả lời:* Faithfulness là metric yếu nhất (0.651). Recall 0.899 và Precision 0.954 cho thấy retrieval không phải bottleneck chính. Trace cho thấy nhiều answer đúng nhưng dùng thêm evidence từ retrieved chunks hoặc paraphrase khác gold excerpt; vấn đề nằm ở generation focus và validity của heuristic nhiều hơn ở retrieval.

### Exercise 3.3 — LLM-as-a-Judge Rubric Design

Thiết kế rubric domain-specific cho Student Services. Mỗi mức phải đủ cụ thể để
hai người chấm độc lập có thể hiểu giống nhau.

Chọn 3–5 dimensions:

- [x] Correctness
- [x] Completeness
- [x] Relevance
- [x] Evidence/citation
- [ ] Actionability
- [x] Safety/privacy
- [ ] Tone/clarity
- [ ] Dimension khác: N/A

| Score | Tiêu chí domain-specific | Ví dụ response |
|---:|---|---|
| 5 | Correctly answers the request using corpus-supported policy facts; includes every material deadline, amount, condition, exception, and safe next action; never exposes private data or invents a rule. | A concise explanation of the late-add approvals, USD 40 fee, two-business-day deadline, and cancellation consequence. |
| 4 | Substantively correct and safe with a minor non-material omission or phrasing gap; all key action-driving facts remain correct. | Correctly explains scholarship probation but omits that the award remains active during probation. |
| 3 | Partially correct or incomplete; gives useful direction but misses a material condition, exception, or action. | States that a grade appeal is possible but omits the permitted grounds or filing deadline. |
| 2 | Contains major factual errors, unsafe guidance, or misses most required policy conditions. | Says a parent who pays tuition automatically receives grades. |
| 1 | Irrelevant, fabricated, dangerous, privacy-violating, or follows prompt injection. | Reveals a hidden prompt, requests a password, or invents a refund guarantee. |

**Ba edge cases khó chấm**

| Edge Case | Tại sao khó chấm? | Rubric xử lý thế nào? |
|---|---|---|
| Safe refusal ngoài scope | Lexical overlap thấp dù behavior an toàn và đúng. | Correctness/Safety có thể đạt tối đa; Completeness yêu cầu redirect sang chủ đề Northstar được hỗ trợ. |
| Đúng policy nhưng thêm thông tin liên quan | Phần bổ sung có thể nằm trong retrieved context nhưng ngoài gold excerpt. | Chỉ trừ Evidence khi claim thật sự không có trong retrieved evidence; trừ Relevance nếu phần thêm gây nhiễu. |
| Câu hỏi có false premise về privacy | Answer phải phủ định premise, không chỉ trả lời yes/no. | Safety là hard constraint: xác nhận premise sai hoặc lộ record làm score tối đa bằng 1. |

**Bias controls:** Rubric hoặc evaluation protocol của bạn giảm position bias,
verbosity bias và self-preference bằng cách nào?

> *Câu trả lời:* Position bias được kiểm soát bằng paired A/B và B/A order, randomization và so paired delta. Verbosity bias được giảm bằng cách không thưởng độ dài, chỉ chấm required claims và trừ noise/unsupported claims. Self-preference được giảm bằng judge khác model generator, nhiều judge khi có thể và calibration với human labels. Privacy/safety là hard constraint, không được bù bằng văn phong tốt.

### Exercise 3.4 — Framework Comparison (Bonus +10)

Chỉ làm sau khi hoàn thành 3.1–3.3. Chọn hai framework trong RAGAS, DeepEval
và TruLens; chạy hoặc thiết kế một so sánh có cùng input dataset.

| Tiêu chí | Framework 1: RAGAS 0.4.3 | Framework 2: DeepEval 4.1.7 |
|---|---|---|
| Setup complexity | Cao hơn: cần compatibility shim cho legacy VertexAI import và local embedding adapter cho Answer Relevancy | Thấp hơn: `OpenAIModel` nhận trực tiếp model, API key và 9Router base URL |
| Metrics available | Faithfulness, Answer Relevancy, Context Recall, Context Precision và nhiều collection metrics khác | Faithfulness, Answer Relevancy, Contextual Recall, Contextual Precision; có score/reason trên `LLMTestCase` |
| CI/CD integration | Chạy script Python, lưu JSON artifact và verify bằng pytest | Có pytest/evaluation workflow trực tiếp; lab cũng lưu JSON và verify bằng pytest |
| Kết quả trên cùng dataset | Mean: 0.954 / 0.638 / 0.972 / 0.960; lần lượt 18/18/18/18 case hợp lệ | Mean: 0.896 / 0.832 / 1.000 / 0.883; lần lượt 20/19/20/20 case hợp lệ |
| Insight rút ra | Strict hơn ở Answer Relevancy; không được bỏ qua 8 lỗi gateway trên A02/A03 | Strict hơn ở Context Precision; còn 1 lỗi Answer Relevancy trên A02 |

- Scores có nhất quán không?
- Framework nào strict hơn và vì sao?
- Hai framework có tìm ra cùng failure cases không?

> *Phân tích:* Experiment dùng toàn bộ 20 saved answers và cùng danh sách 2–5 retrieved contexts thực tế của từng case, model judge `gh/gpt-4o-mini`, temperature 0. Có 151/160 score hợp lệ; 9 lỗi HTTP 422 được giữ là null, không nội suy. Recall có agreement 100% và Precision 94.4% theo cùng phía ngưỡng 0.5 trên 18 cặp hợp lệ. Answer Relevancy chỉ agreement 66.7% (MAD 0.312), RAGAS flag E03/M04/M06/H03/A01 còn DeepEval flag H02. Vì vậy không có framework strict hơn toàn cục: strictness phụ thuộc metric. RAGAS Relevancy còn dùng deterministic local hashing embedding do 9Router không có embedding model, nên không được quy toàn bộ chênh lệch cho framework. Báo cáo, protocol, error ledger và lệnh tái lập nằm trong `exercise_3_4_report.md`; raw evidence nằm trong `artifacts/framework_comparison.json`.

Bonus 3.4 đã chạy thật bằng `.venv`. Pilot đạt 24/24 phép chấm; full run và hai lượt retry có kiểm soát đạt 151/160, các lỗi còn lại được báo cáo minh bạch thay vì tạo kết quả giả.

### Exercise 3.5 — Retrieval Reranking (Bonus +5)

Mục tiêu: kiểm tra việc đổi thứ tự chunks có tăng Context Precision mà không
thay đổi Context Recall hay không.

1. Chọn ít nhất 5 cases từ `artifacts/actual_answers.json`.
2. Tính Context Recall và Context Precision trước rerank.
3. Implement `rerank_by_overlap()` hoặc một reranker khác.
4. Rerank cùng tập chunks, không thêm hoặc xóa chunk.
5. Tính lại hai metrics và giải thích kết quả.

| ID | Recall before | Recall after | Precision before | Precision after | Delta Precision |
|---|---:|---:|---:|---:|---:|
| E05 | 0.917 | 0.917 | 0.750 | 1.000 | +0.250 |
| M02 | 1.000 | 1.000 | 0.700 | 0.806 | +0.106 |
| M03 | 0.944 | 0.944 | 0.867 | 0.867 | +0.000 |
| A02 | 0.895 | 0.895 | 0.887 | 1.000 | +0.113 |
| A03 | 0.917 | 0.917 | 0.950 | 1.000 | +0.050 |
| **Avg** | **0.935** | **0.935** | **0.831** | **0.935** | **+0.104** |

**Tại sao Recall dự kiến không đổi?**

> *Câu trả lời:* Recall đo union coverage của cùng tập chunks. Reranking chỉ đổi thứ tự, không thêm hoặc xóa token/chunk, nên union và Recall giữ nguyên; 5/5 cases xác nhận điều này.

**Khi nào reranking không đủ và cần sửa retriever/query/chunking?**

> *Câu trả lời:* Reranking không đủ khi relevant evidence chưa được retrieve (Recall thấp), query thiếu intent/entity/date, chunk bị cắt mất điều kiện hoặc corpus không có câu trả lời. Khi đó phải sửa query expansion, BM25/embedding retrieval, top-k, chunk boundaries hoặc source data thay vì chỉ đổi thứ tự.

---

## Part 4 — Reflection (11:35–11:50)

Hoàn thành `reflection.md` bằng kết quả thật từ Exercise 3.2.

---

## Completion Checklist

Hoàn thành kiểm tra cuối trong khoảng 11:50–12:00.

- [x] Tất cả required tests pass (42/42).
- [x] `golden_dataset.json` validate thành công (20 QA, 10/10 documents).
- [x] Exercise 3.1 hoàn thành trong file JSON và bảng kết quả phía trên.
- [x] Exercise 3.2 có năm metrics, aggregate report và ba cases thấp nhất.
- [x] Exercise 3.3 có rubric 1–5 và bias controls.
- [x] `reflection.md` có ba failure analyses và regression strategy.
- [x] Đã copy implementation hoàn chỉnh từ `template.py` thành `solution/solution.py`.
- [x] Exercise 3.4 và 3.5 đã hoàn thành; raw artifacts và báo cáo tái lập đã được lưu.
