# Day 14 — Reflection

## Evaluation Report & Failure Analysis

Dùng kết quả thật trong `artifacts/benchmark_results.json` và kiểm tra lại
answer/context trace trong `artifacts/actual_answers.json` trước khi kết luận.

---

## 1. Benchmark Results Summary

**Overall pass rate:** 55.0% (11/20). The RAG run used 9Router at `http://127.0.0.1:20128/v1` with model `gh/gpt-4o-mini`; the full trace is retained in `artifacts/actual_answers.json` and results in `artifacts/benchmark_results.json`.

| Metric | Average | Min | Max | Nhận xét |
|---|---:|---:|---:|---|
| Context Recall | 0.899 | 0.364 | 1.000 | Evidence coverage is high overall; A01 is intentionally out of scope. |
| Context Precision | 0.954 | 0.700 | 1.000 | Retrieved evidence is generally ranked early. |
| Faithfulness | 0.619 | 0.188 | 1.000 | Weakest aggregate metric; generation/lexical mismatch needs attention. |
| Relevance | 0.690 | 0.455 | 1.000 | Most answers address the question, with failures in adversarial cases. |
| Completeness | 0.819 | 0.182 | 1.000 | Policy facts are mostly covered, except the scope response. |
| Overall Score | 0.710 | 0.331 | 0.876 | Overall is answer-side average only. |

**Verified failure-analysis report:** The three lowest cases were A01 (0.331, hallucination), E05 (0.487, hallucination), and E02 (0.569, off_topic). A01 safely refused legal advice but did not redirect to Northstar-supported topics, so the concise gold answer had low lexical completeness. E05 answered the trigger correctly but added the 80% attendance rule, which was not in the selected gold evidence; this lowered faithfulness. E02 correctly gave 24 hours, but its answer did not repeat every expected lexical token, exposing the limitation of word-overlap scoring.

**5 Whys, actionable root causes:** (1) A01 scored low because the scope response was less complete than the expected redirect; the prompt asks for concise answers; it does not explicitly require an in-scope alternative; therefore add a scope-response template and a regression case that requires an example of supported topics. (2) E05 scored low because the generator included adjacent attendance information; the prompt allows retrieved context broadly; no claim-level grounding filter restricts output to the requested fact; therefore add a question-focused evidence filter and verify Faithfulness on E05. (3) E02 failed despite correct substance because set-overlap treats paraphrase and omitted filler tokens as a gap; the metric is intentionally simplified; therefore retain the case but complement lexical metrics with calibrated LLM/human judging before changing the system.

**Failure clusters and priorities:** Cluster 1 (high) is generation grounding/answer focus, affecting E05 and several low-faithfulness results; add a claim-to-context check. Cluster 2 (medium) is scope and adversarial response completeness, affecting A01/A02/A03; add explicit safe-refusal templates. Cluster 3 (medium) is metric sensitivity to paraphrase, affecting E02; calibrate an LLM judge against human labels. The benchmark's own analyzer counted `off_topic=7` and `hallucination=2`; this is a heuristic label, so trace inspection takes priority over the label alone.

**Score interpretation**

- Metrics/cases ở mức Good (0.8–1.0): ____
- Metrics/cases ở mức Needs Work (0.6–0.8): ____
- Metrics/cases ở mức Significant Issues (<0.6): ____

**Failure type distribution**

| Failure Type | Count | Percentage |
|---|---:|---:|
| hallucination | | |
| irrelevant | | |
| incomplete | | |
| off_topic | | |
| refusal | | |

**Chẩn đoán tổng quan:** Vấn đề chính nằm ở retrieval, generation hay cả hai?
Dùng ít nhất hai metrics để bảo vệ kết luận.

> *Câu trả lời:*

---

## 2. Top 3 Worst Failures — 5 Whys

Phân loại failure trước khi đề xuất fix. Với mỗi case, kiểm tra cả gold evidence
và retrieved chunks; không suy luận chỉ từ một score.

### Failure 1

**ID và question:**

> *Điền:*

**Expected answer:**

> *Điền:*

**Actual answer:**

> *Điền:*

**Scores:** Context Recall: ____ | Context Precision: ____ | Faithfulness: ____ |
Relevance: ____ | Completeness: ____ | Overall: ____

**Evidence inspection:** Retriever lấy đúng/thiếu/thừa chunks nào?

> *Câu trả lời:*

| Level | Question | Answer |
|---|---|---|
| Symptom | Vấn đề quan sát được là gì? | |
| Why 1 | Tại sao symptom xảy ra? | |
| Why 2 | Tại sao nguyên nhân trên xảy ra? | |
| Why 3 | Tại sao vấn đề đó chưa được ngăn chặn? | |
| Why 4 | Tại sao cơ chế hiện tại chưa phát hiện hoặc xử lý được? | |
| Why 5 | Root cause có thể hành động được là gì? | |

**Root cause từ `find_root_cause()`:**

> *Paste output:*

**Bạn đồng ý hay không? Dẫn evidence từ trace:**

> *Câu trả lời:*

**Proposed fix cụ thể:**

> *Câu trả lời:*

### Failure 2

**ID và question:**

> *Điền:*

**Expected answer:**

> *Điền:*

**Actual answer:**

> *Điền:*

**Scores:** Context Recall: ____ | Context Precision: ____ | Faithfulness: ____ |
Relevance: ____ | Completeness: ____ | Overall: ____

**Evidence inspection:**

> *Câu trả lời:*

| Level | Question | Answer |
|---|---|---|
| Symptom | Vấn đề quan sát được là gì? | |
| Why 1 | Tại sao symptom xảy ra? | |
| Why 2 | Tại sao nguyên nhân trên xảy ra? | |
| Why 3 | Tại sao vấn đề đó chưa được ngăn chặn? | |
| Why 4 | Tại sao cơ chế hiện tại chưa phát hiện hoặc xử lý được? | |
| Why 5 | Root cause có thể hành động được là gì? | |

**Root cause và proposed fix:**

> *Câu trả lời:*

### Failure 3

**ID và question:**

> *Điền:*

**Expected answer:**

> *Điền:*

**Actual answer:**

> *Điền:*

**Scores:** Context Recall: ____ | Context Precision: ____ | Faithfulness: ____ |
Relevance: ____ | Completeness: ____ | Overall: ____

**Evidence inspection:**

> *Câu trả lời:*

| Level | Question | Answer |
|---|---|---|
| Symptom | Vấn đề quan sát được là gì? | |
| Why 1 | Tại sao symptom xảy ra? | |
| Why 2 | Tại sao nguyên nhân trên xảy ra? | |
| Why 3 | Tại sao vấn đề đó chưa được ngăn chặn? | |
| Why 4 | Tại sao cơ chế hiện tại chưa phát hiện hoặc xử lý được? | |
| Why 5 | Root cause có thể hành động được là gì? | |

**Root cause và proposed fix:**

> *Câu trả lời:*

---

## 3. Failure Clustering

Một root cause có thể tạo ra nhiều failures. Nhóm theo nguyên nhân có thể sửa,
không chỉ nhóm theo tên metric.

| Cluster | Root Cause | Failure IDs | Priority |
|---|---|---|---|
| 1 | | | High/Medium/Low |
| 2 | | | |
| 3 | | | |

**Nếu chỉ được sửa một cluster, bạn chọn cluster nào và vì sao?**

> *Câu trả lời:*

---

## 4. Improvement Log

Paste output của `generate_improvement_log()`:

```text
[paste Markdown table here]
```

**Ba improvement suggestions ưu tiên**

1. ____
2. ____
3. ____

Với mỗi suggestion, nêu metric dự kiến thay đổi và cách đo lại.

| Suggestion | Target metric | Verification method |
|---|---|---|
| | | |
| | | |
| | | |

---

## 5. Regression Testing Strategy

**Câu 1: Khi nào chạy `run_regression()` trong production workflow?**

> *Câu trả lời:*

**Câu 2: Threshold drop 0.05 có phù hợp Student Services không? Vì sao?**

> *Câu trả lời:*

**Câu 3: Metric/failure nào phải block deployment, metric nào chỉ alert?**

> *Câu trả lời:*

**Câu 4: Điền evaluation stages vào flow.**

```text
Code/prompt/retrieval change → [________] → [________] → [________] → Deploy
```

> *Giải thích:*

---

## 6. Continuous Improvement Loop

```text
Evaluate → Analyze → Improve → Augment benchmark → Repeat
```

| Priority | Action | Metric dự kiến cải thiện | Expected impact |
|---:|---|---|---|
| 1 | | | |
| 2 | | | |
| 3 | | | |

**Hai hoặc ba failure cases nào cần thêm vào benchmark ở vòng tiếp theo?**

> *Câu trả lời:*

---

## 7. Final Reflection

**Điều gì trong kết quả benchmark trái với dự đoán ban đầu của bạn?**

> *Câu trả lời:*

**Word-overlap heuristics trong lab có giới hạn gì? Nếu đưa hệ thống vào
production, bạn sẽ thay hoặc bổ sung metric nào?**

> *Câu trả lời:*
