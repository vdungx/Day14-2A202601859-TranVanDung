# Exercise 3.4 — RAGAS vs DeepEval Framework Comparison

## Kết luận

Exercise 3.4 đã được chạy thật trên toàn bộ 20 câu hỏi bằng RAGAS 0.4.3 và
DeepEval 4.1.7. Hai framework cùng dùng model judge `gh/gpt-4o-mini` qua 9Router,
temperature 0, cùng actual answer, expected answer và đúng danh sách retrieved contexts
đã lưu trước đó. Có 151/160 phép chấm hợp lệ; 9 phép còn lại được giữ là
`score=null` kèm lỗi HTTP 422, không nội suy và không thay bằng điểm giả.

Minh chứng máy đọc đầy đủ nằm trong
[`artifacts/framework_comparison.json`](artifacts/framework_comparison.json); pilot
nằm trong [`artifacts/framework_comparison_pilot.json`](artifacts/framework_comparison_pilot.json).

## Protocol và khả năng tái lập

- Dataset: 20/20 records trong `golden_dataset.json`.
- Inference trace: `artifacts/actual_answers.json`; script không gọi lại RAG để sinh answer mới và dùng nguyên 2–5 contexts thực tế mỗi case, không padding.
- Bốn metric chung: Faithfulness, Answer Relevancy, Context Recall và Context Precision.
- Context metrics của cả hai framework dùng `expected_answer` làm reference.
- Failure comparison dùng ngưỡng `< 0.5`.
- Runtime: Python 3.12.10, RAGAS 0.4.3, DeepEval 4.1.7, OpenAI SDK 2.54.0.
- Secret API key chỉ đọc từ `.env`; artifact không lưu key.

Lệnh tái lập trong PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-frameworks.txt
.\.venv\Scripts\python.exe compare_frameworks.py --ids E02 E05 A01 --output artifacts\framework_comparison_pilot.json
.\.venv\Scripts\python.exe compare_frameworks.py --output artifacts\framework_comparison.json --max-concurrency 3
.\.venv\Scripts\python.exe compare_frameworks.py --resume-from artifacts\framework_comparison.json --output artifacts\framework_comparison.json --max-concurrency 1
```

`--resume-from` chỉ gọi lại các ô có `score=null`; khi merge, các điểm đã thành
công được giữ nguyên. Đây là kiểm soát chống cherry-pick khi gateway lỗi tạm thời.

## Kết quả định lượng

| Metric | RAGAS mean | RAGAS hợp lệ | DeepEval mean | DeepEval hợp lệ | MAD trên cặp hợp lệ | Cùng phía ngưỡng 0.5 |
|---|---:|---:|---:|---:|---:|---:|
| Faithfulness | 0.953704 | 18/20 | 0.895833 | 20/20 | 0.125000 (n=18) | 18/18 (100.0%) |
| Answer Relevancy | 0.638377 | 18/20 | 0.832456 | 19/20 | 0.312401 (n=18) | 12/18 (66.7%) |
| Context Recall | 0.972222 | 18/20 | 1.000000 | 20/20 | 0.027778 (n=18) | 18/18 (100.0%) |
| Context Precision | 0.960417 | 18/20 | 0.882500 | 20/20 | 0.089120 (n=18) | 17/18 (94.4%) |

Các mean chỉ tính trên score hợp lệ và luôn đi kèm mẫu số; không nên so mean như
thể hai framework đều có đủ 20 case.

## Failure cases và mức độ nhất quán

| Metric | RAGAS `< 0.5` | DeepEval `< 0.5` | Nhận xét |
|---|---|---|---|
| Faithfulness | Không có trong 18 case hợp lệ | Không có | Cùng không flag failure; điểm tuyệt đối vẫn khác. |
| Answer Relevancy | E03, M04, M06, H03, A01 | H02 | Hai framework bất đồng rõ nhất ở metric này. |
| Context Recall | Không có trong 18 case hợp lệ | Không có | Đồng thuận cao nhất. |
| Context Precision | Không có trong 18 case hợp lệ | H01 | Một bất đồng threshold trên 18 cặp so được. |

Không có một framework “strict hơn” cho mọi metric. RAGAS strict hơn rõ rệt ở
Answer Relevancy (mean thấp hơn và flag 5 case), trong khi DeepEval strict hơn ở
Context Precision (mean thấp hơn và flag H01). Faithfulness và Recall không tạo
failure dưới 0.5 trên các cặp hợp lệ. Vì vậy strictness phụ thuộc định nghĩa metric,
prompt và parser, không phải thuộc tính toàn cục của framework.

## Setup, CI/CD và trải nghiệm sử dụng

| Tiêu chí | RAGAS | DeepEval |
|---|---|---|
| Setup | Phức tạp hơn trong environment này: cần import shim vì RAGAS 0.4.3 còn gọi legacy `langchain_community.chat_models.vertexai`; cần embedding cho Answer Relevancy. | Đơn giản hơn: `OpenAIModel` nhận model, API key và base URL trực tiếp. |
| Metric API | Modern collection metrics trả `MetricResult`; context metrics có reference rõ ràng. | `LLMTestCase` gom input/output/reference/retrieval context; metric có score và reason. |
| CI/CD | Chạy được bằng script Python và kiểm tra artifact trong pytest. | Có tích hợp pytest/evaluation workflow trực tiếp; vẫn có thể dùng script như lab này. |
| Điểm mạnh | API metric tách bạch; Recall/Precision gần DeepEval trên các cặp hợp lệ. | Setup OpenAI-compatible thuận tiện; reason chi tiết hơn trong artifact. |
| Hạn chế quan sát được | Runtime import không tương thích LangChain mới; A02/A03 structured output thất bại qua gateway. | A02 Answer Relevancy thất bại qua gateway; điểm metric không tương đương trực tiếp với RAGAS. |

RAGAS Answer Relevancy cần embedding nhưng 9Router hiện không cung cấp embedding
model trong cấu hình lab. Experiment dùng embedding local 1024 chiều, deterministic,
hash token và bigram; đây là hạn chế phương pháp quan trọng. Nó giúp run tái lập và
không thêm provider thứ hai, nhưng làm cho chênh lệch Answer Relevancy không thể quy
hoàn toàn cho framework.

## Error accounting và nhật ký chạy

| Run | Phạm vi | Thời gian quan sát | Kết quả |
|---|---|---:|---|
| Pilot | E02, E05, A01; 2 framework × 4 metric | 253.9 s | 24/24 score hợp lệ. |
| Full ban đầu | 20 case, concurrency 3 | 535.6 s | Gateway 422 tạo các ô null; không dừng run. |
| Retry 1 | Chỉ ô null, concurrency 1 | 300.6 s | Phục hồi đến 151/160. |
| Retry 2 | Chỉ lỗi còn lại trên A02/A03 | 21.8 s | Không phục hồi thêm; lỗi tái lập. |

Lỗi cuối cùng:

- RAGAS: cả 4 metric của A02 và A03 — `InstructorRetryException`, HTTP 422 từ 9Router.
- DeepEval: Answer Relevancy của A02 — `UnprocessableEntityError`, HTTP 422 từ 9Router.
- Không có score NaN được xem là thành công; mọi score null đều có error string.

## Insight và quyết định

1. Hai framework tương đối nhất quán cho retrieval metrics: Recall đồng thuận 100%
   và Precision 94.4% theo cùng phía ngưỡng trên các cặp hợp lệ.
2. Answer Relevancy không thể thay thế lẫn nhau: agreement chỉ 66.7%, MAD 0.312401,
   và tập failure gần như khác nhau.
3. Benchmark LLM-as-judge cần báo cả coverage và lỗi provider. Chỉ công bố mean sẽ
   che mất việc RAGAS thiếu A02/A03 và DeepEval thiếu một phép chấm A02.
4. Trong CI, nên chạy một pilot nhỏ trước, giới hạn concurrency, cache kết quả và
   đặt quality gate cho `successful/expected`, không chỉ gate theo mean score.
5. Nếu cần kết luận chắc hơn về Answer Relevancy, bước tiếp theo là cung cấp cùng
   một semantic embedding model cho RAGAS và hiệu chỉnh cả hai framework bằng human
   labels. Không nên dùng run hiện tại để tuyên bố framework nào chính xác hơn.

Mức tin cậy: **cao** cho input parity, error accounting và các thống kê đã tính;
**trung bình** cho so sánh retrieval metrics vì judge vẫn là LLM; **thấp-trung bình**
cho so sánh Answer Relevancy vì embedding pipeline không đối xứng.

## Quality gate và recovery audit bổ sung

`audit_framework_comparison.py` tính lại summary, kiểm tra 20 ID, invariant
`score=null ⇔ error!=null` và sinh
`artifacts/framework_quality_gate.json`. Trạng thái hiện tại là
`complete_with_provider_limitations`: yêu cầu lab pass, coverage 151/160, production
completeness chưa pass.

Hai pilot recovery không được trộn vào main run:

- `gh/gpt-4o`: 0/16 phép chấm A02/A03 thành công, tiếp tục trả HTTP 422.
- `gc/gemini-2.5-flash`: 11/16 thành công; RAGAS còn lỗi JSON structured-output.

Endpoint embedding `text-embedding-3-small` qua 9Router trả HTTP 400
`No credentials for provider: openai`. Vì vậy không thể khắc phục tính bất đối xứng
Answer Relevancy bằng cùng semantic embedding trong environment hiện tại. Quality
gate buộc `production_ready=false` cho đến khi có embedding provider và một full run
160/160 bằng cùng judge/protocol.

Giao diện demo trong `demo/` biểu diễn trực quan đúng trạng thái này; không che chín
lỗi và không dùng recovery score làm điểm thay thế.

## Tài liệu framework dùng để đối chiếu API

- [RAGAS — Evaluate a simple RAG system](https://docs.ragas.io/en/stable/getstarted/rag_eval/)
- [RAGAS — Customize models](https://docs.ragas.io/en/stable/howtos/customizations/customize_models/)
- [DeepEval — RAG evaluation quickstart](https://deepeval.com/docs/getting-started-rag)
- [DeepEval — OpenAI and OpenAI-compatible models](https://deepeval.com/integrations/models/openai)
