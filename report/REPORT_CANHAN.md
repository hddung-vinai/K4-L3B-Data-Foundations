# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Hoàng Đức Dũng
**Nhóm:** Finding Vinno
**Ngày:** 20/9/2026

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**
> Cosine đo góc giữa hai vector embedding. Cosine tiến về 1 ⟹ góc gần 0° ⟹ hai vector chỉ về cùng một hướng, tức model đánh giá hai đoạn văn bản nói về cùng chủ đề / cùng ý. Cosine ≈ 0 ⟹ vuông góc ⟹ không liên quan.

**Ví dụ có độ tương tự CAO:**
- Câu A: "Thời hạn bảo hành máy mới là 12 tháng." 
- Câu B: "Sản phẩm mới được bảo hành trong vòng một năm."
- Tại sao tương đồng: Cùng chủ đề (thời hạn bảo hành), cùng thông tin (12 tháng = 1 năm), chỉ khác cách diễn đạt — embedding mã hoá nghĩa, không mã hoá mặt chữ.

**Ví dụ có độ tương tự THẤP:**
- Câu A: "Thời hạn bảo hành máy mới là 12 tháng."
- Câu B: "Con cá bơi dưới nước"
- Tại sao khác:  khác hoàn toàn chủ đề, chủ thể và lĩnh vực; không có khái niệm nào chung nên hai vector gần như vuông góc.

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**
> Vì cosine bỏ qua độ lớn vector, chỉ so hướng. Độ lớn thường phản ánh độ dài văn bản chứ không phản ánh nghĩa, nên hai đoạn cùng chủ đề nhưng chênh lệch độ dài sẽ có Euclid lớn trong khi góc vẫn nhỏ. Ngoài ra ở số chiều cao, khoảng cách Euclid giữa mọi cặp điểm có xu hướng co về gần nhau nên kém phân biệt.
>
> Lưu ý thêm: trong repo này embedding đã được chuẩn hoá về độ dài 1 (`src/embeddings.py:29` với `MockEmbedder`, và `normalize_embeddings=True` ở `:44` với `LocalEmbedder`). Khi vector đã chuẩn hoá thì `‖a−b‖² = 2 − 2·cos(a,b)`, nghĩa là cosine và Euclid cho **cùng một thứ tự xếp hạng**. Lúc đó cosine vẫn được ưu tiên vì giá trị nằm gọn trong `[-1, 1]`, dễ đặt ngưỡng và dễ so sánh giữa các truy vấn khác nhau.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> *Trình bày phép tính:* Số chunk = ceil((10000 − 50) / 450) = ceil(9950 / 450) = ceil(22,11) = 23
> *Đáp án:* 23 chunks

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**
> ceil((10000 − 100) / 400) = ceil(24,75) = 25 chunk, tức tăng 2 chunk, vì bước nhảy giảm từ 450 xuống 400 nên cần nhiều lượt cắt hơn để phủ hết tài liệu.
> Muốn độ overlap nhiều hơn vì để tránh làm đứt đôi một ý ngay tại ranh giới chunk. Ví dụ trong corpus của nhóm, nếu câu "Nhà Bán cam kết thời gian bảo hành tối đa không quá 30 ngày" bị cắt giữa chừng thì không chunk nào chứa trọn thông tin, retrieval trả về mảnh vụn và không trích được gold answer. Overlap lớn khiến mỗi vùng ranh giới xuất hiện trong hai chunk kề nhau, tăng xác suất có ít nhất một chunk chứa nguyên vẹn ý đó. Cái giá phải trả: nhiều chunk hơn ⟹ index lớn hơn, chi phí embedding cao hơn, và các chunk gần trùng nhau có thể cùng chiếm chỗ trong top-k, làm giảm độ đa dạng kết quả trả về.

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi lập trình (implement) các phần chính trong gói `src`.

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:
> Dùng regex `(?<=[.!?])\s+` (`src/chunking.py:45`): lookbehind để cắt *sau* dấu câu nên dấu `.` `!` `?` được giữ lại trong câu, còn `\s+` phủ luôn cả `". "` lẫn `".\n"` mà không cần viết riêng từng trường hợp. Sau khi tách thì `strip()` từng câu và loại câu rỗng, rồi gom theo lô `max_sentences_per_chunk` bằng slice `sentences[i:i+step]`.
> Edge case đã xử lý: text rỗng hoặc chỉ gồm khoảng trắng → trả `[]`; `max_sentences_per_chunk <= 0` → ép về 1 bằng `max(1, ...)` trong `__init__` để tránh slice bước 0 gây vòng lặp vô hạn; câu cuối không có khoảng trắng phía sau vẫn được giữ vì `split` trả về phần đuôi.
> Hạn chế đã biết: regex này cắt nhầm ở viết tắt kiểu "TS. Nguyễn" hay "30.000 đ", chấp nhận được cho lab vì corpus bảo hành chủ yếu là câu trần thuật thường.

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:
> Thuật toán gồm hai pha: **cắt → gộp**. Pha cắt là `_split` đệ quy theo thứ tự ưu tiên separator `["\n\n", "\n", ". ", " ", ""]` — lấy separator đầu tiên cắt đoạn hiện tại, rồi gọi đệ quy từng mảnh với phần separator còn lại, nên chỉ những mảnh *vẫn còn quá dài* mới bị cắt tiếp bằng ranh giới mịn hơn. Ý tưởng: ưu tiên giữ nguyên đoạn văn, chỉ hạ xuống mức dòng → câu → từ khi bắt buộc.
> **Hai base case** (`src/chunking.py:105-113`): (1) `len(current_text) <= chunk_size` → trả nguyên đoạn, không cắt nữa; (2) hết separator mà vẫn dài → cắt cứng theo `chunk_size` để hàm luôn kết thúc, kể cả khi người dùng truyền `separators=[]` hoặc văn bản không có khoảng trắng nào.
> Pha gộp `_merge` (`src/chunking.py:89`) là phần tôi thêm ngoài khung đề bài: `_split` đơn thuần sẽ trả về vụn rất nhỏ (cắt ở mức `" "` là ra từng từ một), nên tôi duyệt tham lam và dán các mảnh liền kề lại chừng nào tổng độ dài còn `<= chunk_size`. Nhờ vậy chunk cuối cùng bám sát `chunk_size` thay vì vụn thành từng từ — điều kiện cần để embedding còn mang đủ ngữ cảnh cho retrieval.

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:
> Mọi `Document` đi qua `_make_record` (`src/store.py:44`) để chuẩn hóa về một dict thống nhất `{id, doc_id, index, content, metadata, embedding}`, trong đó `embedding` được tính ngay lúc ghi bằng `self._embedding_fn` — nhờ tiêm hàm embedding qua constructor mà test dùng `_mock_embed` còn demo thật dùng `LocalEmbedder` mà không phải sửa store. Hai chi tiết nhỏ nhưng quan trọng: metadata được **copy** (`dict(doc.metadata or {})`) nên store không bao giờ sửa dict của người gọi; và `doc_id` được suy ra bằng `_base_doc_id` — cắt phần sau dấu `#` của `doc.id`, nên nhiều chunk `"warranty#0"`, `"warranty#1"` đều quy về cùng `doc_id = "warranty"` và `delete_document("warranty")` xóa được trọn tài liệu thay vì chỉ một mảnh.
> Quyết định thiết kế đáng chú ý: **bỏ hẳn nhánh ChromaDB**, chỉ dùng list in-memory. Lý do: không test nào cần Chroma, `requirements.txt` không cài nó, và khung code ban đầu có một cái bẫy — `self._use_chroma = True` được gán *trước khi* client thực sự được tạo, nên trên máy nào tình cờ có `chromadb` thì mọi method sẽ rẽ vào nhánh chưa cài đặt và toàn bộ test sập. Một đường dữ liệu duy nhất thì không có hai hành vi để lệch nhau.
> `search` ủy quyền hết cho `_search_records` (`src/store.py:60`): embed câu hỏi một lần, chấm điểm từng bản ghi bằng `compute_similarity` (cosine), sắp xếp giảm dần rồi cắt `top_k`. Tôi dùng cosine thay vì dot product thuần như gợi ý trong docstring, vì cosine tự chuẩn hóa độ dài vector nên kết quả đúng kể cả khi đổi sang backend embedding không trả vector đơn vị. Kết quả trả về cố tình **không kèm `embedding`** — vector hàng trăm chiều sẽ làm bẩn output khi in ra terminal — và dùng `index` (thứ tự nạp) để phá hòa khi hai chunk cùng điểm, cho thứ hạng tất định.

**`search_with_filter` + `delete_document`** — hướng tiếp cận:
> **Lọc trước, tìm sau** (pre-filtering, `src/store.py:102`): thu hẹp `self._store` bằng điều kiện `all(metadata.get(k) == v)` trên toàn bộ cặp key-value của `metadata_filter`, rồi mới đưa tập ứng viên đó vào `_search_records`. Nếu lọc sau thì `top_k` bị "tiêu" vào các chunk sẽ bị loại, ví dụ tìm top-3 mà cả 3 đều thuộc phòng ban khác thì kết quả trả về rỗng dù kho vẫn có tài liệu đúng phòng ban. Khi `metadata_filter` rỗng/None thì bỏ qua bước lọc, nên `search_with_filter` trả về đúng bằng `search` — đây chính là điều test `test_no_filter_returns_all_candidates` kiểm tra.
> `delete_document` (`src/store.py:118`) xóa theo `doc_id` chứ không theo `id` của từng chunk, vì một tài liệu sau khi chunk sẽ nằm rải ở nhiều bản ghi; `_make_record` đã ghi sẵn `metadata["doc_id"]` (đã cắt hậu tố `#n`) từ lúc nạp nên luôn có khóa này để gom nhóm. Cách xóa là lọc ra list mới `remaining` rồi so sánh độ dài trước/sau — dài bằng nhau nghĩa là không có gì khớp, trả `False`; ngắn hơn thì gán lại `self._store` và trả `True`. Lọc-tạo-list-mới an toàn hơn `remove()` trong vòng lặp vì không sửa list đang duyệt.

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:
> Ba bước đúng khuôn RAG: `store.search(question, top_k)` → dựng context → `llm_fn(prompt)`. Prompt được tách ra thành hằng `PROMPT_TEMPLATE` ở cấp lớp (`src/agent.py:18`) thay vì nối chuỗi trong thân hàm, để sau này tinh chỉnh prompt chỉ phải sửa một chỗ và có thể ghi đè bằng subclass.
> Cấu trúc prompt gồm 4 khối theo thứ tự: **vai trò → quy tắc → NGỮ CẢNH → CÂU HỎI**, kết thúc bằng nhãn `TRẢ LỜI:` để mồi mô hình sinh tiếp. Ba quy tắc được nêu tường minh — chỉ dùng thông tin trong ngữ cảnh, nói rõ khi không đủ thông tin, và trích dẫn theo số — nhằm hạn chế bịa đặt (hallucination), vốn là rủi ro lớn nhất của RAG khi retrieval trả về chunk không liên quan.
> Cách inject context: `_build_context` (`src/agent.py:36`) đánh số từng chunk `[1]`, `[2]`... và gắn kèm `(nguồn: ...)` lấy từ `metadata['source']`, fallback sang `doc_id` rồi `"unknown"`. Đánh số là điều kiện cần để quy tắc trích dẫn ở trên có ý nghĩa — người đọc câu trả lời lần ngược được về đúng đoạn văn bản gốc. Ngoài ra có chốt chặn sớm: nếu `search` trả rỗng thì trả thẳng `NO_CONTEXT_MESSAGE`, không gọi LLM — tiết kiệm một lượt gọi API và tránh việc mô hình tự bịa khi context trống.

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

> `pytest` không có sẵn trong `.venv` của máy chạy nên bộ test được chạy bằng `unittest` — cùng các test case, chỉ khác runner.

```
$ python -m unittest discover -s tests -t . -v

test_root_main_entrypoint_exists (tests.test_solution.TestProjectStructure...) ... ok
test_src_package_exists (tests.test_solution.TestProjectStructure...) ... ok
test_chunker_classes_exist (tests.test_solution.TestClassBasedInterfaces...) ... ok
test_mock_embedder_exists (tests.test_solution.TestClassBasedInterfaces...) ... ok
... (38 test còn lại) ...
test_single_sentence_max_gives_many_chunks (tests.test_solution.TestSentenceChunker...) ... ok

----------------------------------------------------------------------
Ran 42 tests in 0.003s

OK
```

**Số lượng bài test vượt qua (pass):** 42 / 42

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

> **Ghi chú phương pháp:** `MockEmbedder` mặc định sinh vector bằng cách băm MD5 chuỗi rồi chạy bộ sinh số giả ngẫu nhiên (`src/embeddings.py:23-28`), **không mang ngữ nghĩa**. Kiểm chứng: hai câu giống hệt nhau chỉ khác dấu câu cuối (`.` → `!`) cho cosine rơi từ `+1.0000` xuống `+0.1262` — ngang mức ngẫu nhiên. Vì vậy toàn bộ số đo dưới đây chạy trên **`OpenAIEmbedder` (`text-embedding-3-small`)**, cùng backend với benchmark ở mục 5, để kết quả hai mục so sánh được với nhau.

| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | Thời hạn bảo hành máy mới là 12 tháng. | Sản phẩm mới được bảo hành trong vòng một năm. | **cao** — cùng nghĩa, chỉ khác cách diễn đạt | `+0.6641` | ✅ Đúng |
| 2 | Nhà Bán phải phản hồi trong 02 ngày làm việc. | Con cá bơi dưới nước. | **thấp** — khác hoàn toàn lĩnh vực | `+0.2711` | ✅ Đúng |
| 3 | Sản phẩm này được bảo hành. | Sản phẩm này không được bảo hành. | **thấp** — nghĩa trái ngược nhau | `+0.8853` | ❌ **Sai hoàn toàn** |
| 4 | Thời gian bảo hành tối đa không quá 30 ngày. | Nhà Bán cam kết hoàn tất bảo hành trong vòng một tháng. | **cao** — 30 ngày ≈ một tháng | `+0.5726` | ⚠️ Thấp hơn dự đoán |
| 5 | Chính sách đổi trả dành cho người mua. | Quy định bảo hành dành cho nhà bán hàng. | **thấp** — khác cả chủ đề lẫn đối tượng | `+0.5541` | ⚠️ Cao hơn dự đoán |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**
> **Cặp 3 là bất ngờ lớn nhất: `+0.8853` — cao nhất trong cả năm cặp, dù hai câu nói ngược hẳn nhau.** Còn choáng hơn khi so với cặp 1 (`+0.6641`), vốn là hai câu *thật sự đồng nghĩa*. Nói cách khác, model coi "được bảo hành" và "**không** được bảo hành" giống nhau hơn là "12 tháng" và "một năm".
>
> Lý do: embedding mã hoá **chủ đề và bối cảnh từ vựng**, không mã hoá **giá trị chân lý**. Hai câu ở cặp 3 chia sẻ gần như toàn bộ từ ngữ, chỉ chênh một chữ "không" — một token ngắn, tần suất cực cao, đóng góp rất ít vào vector cuối. Trong khi đó cặp 1 phải bắc cầu giữa hai cách diễn đạt khác nhau ("12 tháng" ↔ "một năm", "thời hạn" ↔ "trong vòng"), việc khó hơn nhiều.
>
> **Hệ quả trực tiếp cho hệ thống RAG của nhóm:** với câu hỏi "Sản phẩm này có được bảo hành không?", retrieval hoàn toàn có thể đưa lên top-1 một chunk thuộc mục *"Những trường hợp **không** được bảo hành"* và agent sẽ trả lời ngược. Đây không phải giả thuyết — nó **đã xảy ra** ở câu 4 của benchmark mục 5: top-1 là mục 2 "Những trường hợp không được bảo hành" trong khi câu hỏi hỏi về *điều kiện được* bảo hành. Cặp 4 và 5 củng cố cùng một bài học ở chiều ngược lại: cosine bị kéo mạnh bởi việc dùng chung từ vựng miền ("bảo hành", "Nhà Bán", "đổi trả"), nên hai câu khác đối tượng vẫn được `+0.5541`. Chính vì vậy `metadata_filter` theo `audience` là cần thiết — thứ mà embedding không tách được thì phải tách bằng metadata.

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá của nhóm** trên mã nguồn cá nhân của bạn trong gói `src`. **5 câu hỏi này phải trùng với các thành viên cùng nhóm** (xem `REPORT_NHOM.md`).

> **Cấu hình đo:** `SentenceChunker(max_sentences_per_chunk=4)` · embedding `text-embedding-3-small` · LLM `gpt-4o-mini` · `top_k=3`. Output đầy đủ: `ket_qua_benchmark.txt` (sinh bởi `python bench.py --compare`).
>
> **Cách chấm — hai mức.** Cột "Có liên quan" **không** chỉ kiểm `doc_id` nằm trong top-3, mà kiểm ở mức nội dung: mỗi câu hỏi khai báo một `gold_phrase` trích nguyên văn từ tài liệu, và chunk chỉ được tính là liên quan khi **chứa nguyên chuỗi đó**. Thang điểm theo `docs/SCORING.md`: 2đ nếu ở top-1, 1đ nếu ở top-2/3, 0đ nếu vắng.

| # | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Điểm Score | Có liên quan không? (Relevant) | Câu trả lời của Agent (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | Theo chính sách Hoàng Hà Mobile, khách hàng được đổi mới miễn phí trong thời gian nào? | `hoanghamobile-warranty-buyer#1` — "### 1. Đối tượng áp dụng... Trong 15 hoặc 30 ngày đầu kể từ ngày mua — Đổi mới miễn phí 100%..." | +0.6956 | Có (top-1) — **2/2** | "Khách hàng được đổi mới miễn phí trong 15 hoặc 30 ngày đầu kể từ ngày mua, tùy theo dòng sản phẩm" — khớp gold |
| 2 | Trong mô hình Seller Center, Nhà Bán có bao nhiêu ngày làm việc để xác nhận phương án xử lý yêu cầu đổi trả? | `tiki-seller-warranty-faq#32` — "Khi phát sinh đơn hàng bồi thường, Nhà Bán cần làm gì? Bước 1: Tiki sẽ..." | +0.6499 | **Không — 0/2** (gold ở hạng 12/50) | "Nhà Bán có 02 ngày làm việc để xác nhận phương án xử lý..." — agent trả lời **đúng** dù chunk gold không lọt top-3 |
| 3 | Nếu Nhà Bán không phản hồi, Tiki sẽ xử lý yêu cầu của Khách Hàng như thế nào? | `tiki-seller-warranty-faq#3` — "Trường hợp Nhà Bán **từ chối** yêu cầu đổi – trả – bảo hành của Khách hàng..." | +0.7696 | **Không — 0/2** (gold ở hạng 14/50; lấy nhầm mục *từ chối* thay vì mục *không phản hồi*) | "Tiki sẽ thực hiện theo yêu cầu đổi – trả của Khách Hàng..." — đúng hướng nhưng không nêu được vế *cấn trừ kỳ thanh toán* |
| 4 | Sản phẩm cần thỏa những điều kiện nào để được bảo hành miễn phí? | `shopee-warranty-buyer#2` — "Những trường hợp **không** được bảo hành hoặc phát sinh phí bảo hành" | +0.6522 | Có (hạng 2) — **1/2** | "Sản phẩm cần thỏa những điều kiện sau: 1. Sản phẩm bị lỗi kỹ thuật do nhà sản xuất..." — khớp gold |
| 5 | Thời gian bảo hành tối đa là bao lâu? | `tiki-seller-warranty-faq#6` — "Thời gian Nhà Bán cam kết bảo hành là bao lâu? Nhà Bán cam kết thời gian..." | +0.7082 | Có (top-1) — **2/2** | "Thời gian bảo hành tối đa là 30 ngày đối với Nhà Bán..." — khớp gold |

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?**

- Chấm ở **mức tài liệu** (chỉ kiểm `doc_id`): **5 / 5** — cả 5 câu đều lấy đúng file.
- Chấm ở **mức nội dung** (chunk phải chứa `gold_phrase`): **3 / 5** (câu 1, 4, 5), tổng **5/10 điểm**, top-1 2/5, MRR 0.500.

Chênh lệch 5/5 so với 5/10 là điểm đáng chú ý nhất của bài đo: cách chấm ngây thơ thổi phồng kết quả gấp đôi. Nguyên nhân của hai câu trượt (2 và 3) không phải là retrieval lấy sai tài liệu — cả hai đều lấy đúng `tiki-seller-warranty-faq` — mà là **lấy sai mục trong cùng tài liệu**. Chunk gold của câu 2 nằm tận hạng 12/50, câu 3 hạng 14/50, tức trượt xa chứ không sát nút. Lý do nằm ở chính chiến lược sentence: nó cắt cứ đủ 4 câu là cắt, bất kể đang ở giữa mục nào, nên chunk `tiki-seller-warranty-faq#22` chứa đáp án câu 2 lại vắt qua hai mục FAQ — nửa đầu là "Bước 4" của mục 7, nửa sau mới là mục 8. Embedding của chunk lai hai chủ đề nên không khớp hẳn câu hỏi nào.

> **Một quan sát đáng chú ý: agent vẫn trả lời đúng câu 2 dù retrieval trượt.** Chunk chứa `gold_phrase` không lọt top-3, nhưng các chunk lân cận vẫn nhắc tới mốc "02 ngày làm việc" ở ngữ cảnh khác, đủ để LLM tổng hợp ra câu trả lời đúng. Điều này cho thấy hai chỉ số *retrieval đúng chunk* và *agent trả lời đúng* không trùng nhau — `docs/SCORING.md` đòi cả hai, và ở đây chúng lệch nhau đúng một câu. Không nên kết luận hệ thống tốt chỉ vì câu trả lời cuối cùng nghe hợp lý: lần này là may, lần khác chunk lân cận có thể chứa con số của một điều khoản khác và agent sẽ bịa ra đáp án sai mà vẫn trôi chảy.

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**
> Từ chiến lược `RecursiveChunker` của Khuê: **không có chiến lược chunking nào thắng toàn diện**, và điều đó chỉ lộ ra khi chấm từng câu thay vì nhìn tổng điểm. Chạy cùng 5 câu, cùng corpus, cùng embedding, chỉ khác dòng chọn chunker, kết quả là:
>
> | Câu | Dạng hỏi | fixed | recursive | sentence |
> |---|---|---|---|---|
> | 1 | hỏi điều kiện | 0/2 | 0/2 | **2/2** |
> | 2 | tra số liệu | 0/2 | **2/2** | 0/2 |
> | 3 | hỏi quy trình | 0/2 | **2/2** | 0/2 |
> | 4 | liệt kê | 0/2 | 0/2 | **1/2** |
> | 5 | cần lọc metadata | **2/2** | **2/2** | **2/2** |
>
> Recursive thắng ở hai câu mà sentence trượt (2 và 3), còn sentence thắng ở đúng hai câu recursive trượt (1 và 4) — bù trừ gần như hoàn hảo. Lý do nằm ở cấu trúc tài liệu: recursive cắt theo `

` nên bám sát ranh giới mục của FAQ Tiki, hợp với câu 2 và 3 vốn hỏi thẳng vào một mục FAQ; còn sentence cho chunk ngắn và đặc thông tin, hợp với câu 1 và 4 nơi đáp án gói trong vài câu văn liền nhau.

> Bài học tôi rút ra: tổng điểm che mất thông tin quan trọng nhất. Nếu chỉ báo cáo "recursive 6/10, sentence 5/10" thì kết luận sẽ là "recursive tốt hơn", trong khi thực tế hai chiến lược **bổ sung cho nhau**. Hướng đi đúng cho hệ thống thật là kết hợp — chunk theo cấu trúc trước, rồi cắt nhỏ theo câu bên trong mỗi mục — chứ không phải chọn một cái rồi bỏ cái kia.

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Khởi động (Warm-up) | 5 / 5 |
| Hướng tiếp cận của tôi (My Approach) | 10 / 10 |
| Hoàn thiện code (Core Implementation — tests) | 30 / 30 |
| Dự đoán độ tương tự (Similarity Predictions) | 5 / 5 |
| Kết quả truy xuất của tôi (Competition Results) | 10 / 10 |
| **Tổng phần cá nhân** | **60 / 60** |
