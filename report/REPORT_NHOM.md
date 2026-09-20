# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** Finding Vinno
**Thành viên:** Ngô Hoàng Thụy Khuê, Hoàng Đức Dũng, Nguyễn Phúc Huy
**Ngày:** 20/9/2026

> **Nộp 1 bản / nhóm.** Phần cá nhân (hướng tiếp cận, kết quả riêng, dự đoán…) mỗi thành viên nộp riêng trong `REPORT_CANHAN.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần nhóm: 40** = Lựa chọn tài liệu (10) + Thiết kế chiến lược (15) + Chất lượng truy xuất (10) + Thuyết trình (5).

---

## 1. Lựa chọn tài liệu (Document Set Quality) — Nhóm (10 điểm)

### Chủ đề (Domain) & Lý Do Chọn

**Chủ đề:** Chính sách đổi trả, bảo hành và quy trình xử lý yêu cầu cho khách mua và Nhà Bán trên các sàn thương mại điện tử.

**Tại sao nhóm chọn chủ đề này?**
> Chủ đề này rất phù hợp để đánh giá retrieval vì cùng một thực thể nghiệp vụ có thể xuất hiện dưới nhiều góc nhìn: khách mua, Nhà Bán và mô hình vận hành. Bên cạnh đó, dữ liệu có sẵn trong corpus chứa nhiều đoạn văn cụ thể, dễ kiểm chứng bằng metadata `audience` và `category` để so sánh độ hiệu quả của việc lọc ngữ cảnh.

### Danh sách tài liệu (Data Inventory)

| # | Tên tài liệu | Nguồn (Source URL) | Ngày lấy / Phiên bản | Số ký tự | Metadata đã gán |
|---|--------------|------------|--------------------|----------|-----------------|
| 1 | hoanghamobile-warranty-buyer.md | https://hoanghamobile.com/chinh-sach-bao-hanh | 2026-09-20 / áp dụng từ 2025-09-29 | 7.969 | `audience=buyer`, `category=warranty-policy`, `language=vi` |
| 2 | tiki-seller-warranty-faq.md | https://hocvien.tiki.vn/faq/cau-hoi-thuong-gap-ve-xu-ly-doi-tra-bao-hanh/ | 2026-09-20 / not-stated | 13.746 | `audience=seller`, `category=warranty-process`, `language=vi` |
| 3 | tiki-seller-warranty-sd.md | https://hocvien.tiki.vn/faq/huong-dan-quy-trinh-xu-ly-doi-tra-bao-hanh-mo-hinh-sd/ | 2026-09-20 / not-stated | 7.132 | `audience=seller`, `category=warranty-process`, `language=vi` |
| 4 | tiki-seller-warranty-dropship.md | https://hocvien.tiki.vn/faq/huong-dan-quy-trinh-xu-ly-doi-tra-bao-hanh-mo-hinh-dropship/ | 2026-09-20 / not-stated | 10.832 | `audience=seller`, `category=warranty-process`, `language=vi` |
| 5 | tiki-seller-warranty-fbt.md | https://hocvien.tiki.vn/faq/mo-hinh-fbt-huong-dan-quy-trinh-xu-ly-doi-tra-bao-hanh/ | 2026-09-20 / not-stated | 3.217 | `audience=seller`, `category=warranty-process`, `language=vi` |
| 6 | shopee-warranty-buyer.md | https://help.shopee.vn/portal/4/article/79046 | 2026-09-20 / not-stated | 2.949 | `audience=buyer`, `category=warranty-policy`, `language=vi` |

**Tổng:** 6 tài liệu · 45.845 ký tự (phần thân, đã trừ frontmatter) · phân bố `audience`: buyer 2 / seller 4.

> Số ký tự đếm bằng `len(body)` sau khi tách frontmatter, đối chiếu trực tiếp từ file trong `data/warranty/`. Toàn bộ 6 URL đều là trang công khai và được ghi trong `data/warranty/sources.csv` với `license_or_permission = public-source` — **không có tài liệu nội bộ nào trong corpus**.

**Danh sách kiểm tra quản trị dữ liệu (Data governance checklist):**
- [x] Tập tài liệu (Corpus) chỉ chứa nguồn công khai/được phép dùng và không chứa dữ liệu cá nhân, thông tin đăng nhập hoặc tài liệu nội bộ.
- [x] Mỗi tài liệu có `source_url`, `retrieved_at`, `document_version` (hoặc ngày hiệu lực) trong metadata.

### Cấu trúc Metadata (Metadata Schema)

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho truy xuất (retrieval)? |
|----------------|------|---------------|-------------------------------|
| audience | string | buyer / seller | Giúp nhóm dữ liệu theo người dùng, giảm sai lệch giữa các chính sách khác nhau. |
| category | string | warranty-policy / warranty-process | Cho phép lọc theo loại nội dung để tránh trả lời nhầm giữa chính sách và quy trình vận hành. |
| source_url | string | https://... | Dễ kiểm tra nguyên gốc, xác thực và theo dõi phiên bản tài liệu. |
| retrieved_at | string | 2026-09-20 | Theo dõi thời điểm hợp nhất dữ liệu và sửa đổi nếu cần. |
| document_version | string | ap-dung-tu-2025-09-29 | Giúp lịch sử phiên bản và so sánh hiệu lực chính sách. |

---

## 2. Thiết kế chiến lược (Strategy Design) — Nhóm (15 điểm)

> Mỗi thành viên thử **một chiến lược khác nhau** trên cùng bộ tài liệu; nhóm tổng hợp và so sánh ở đây.

### Phân tích đường cơ sở (Baseline Analysis)

Chạy `ChunkingStrategyComparator().compare()` trên 2-3 tài liệu:

> Số đo thật từ `ChunkingStrategyComparator().compare(body, chunk_size=600)`, chạy trên 3 tài liệu đại diện. **Đã tách bỏ frontmatter YAML trước khi so sánh** — nếu không, khối 9 dòng metadata sẽ bị tính vào độ dài chunk và làm lệch cả ba cột.

| Tài liệu | Chiến lược (Strategy) | Số lượng Chunk | Độ dài trung bình | Giữ được ngữ cảnh không? |
|-----------|----------|-------------|------------|-------------------|
| hoanghamobile-warranty-buyer.md | FixedSizeChunker (`fixed_size`) | 14 | 569 (min 169 – max 600) | Kém — cắt theo số ký tự nên đứt giữa câu và giữa mục |
| hoanghamobile-warranty-buyer.md | SentenceChunker (`by_sentences`) | 25 | 317 (min 184 – max 573) | Khá — không bao giờ đứt giữa câu, nhưng bỏ qua ranh giới mục |
| hoanghamobile-warranty-buyer.md | RecursiveChunker (`recursive`) | 16 | 494 (min 152 – max 579) | Tốt nhất — ưu tiên cắt ở `\n\n` nên bám ranh giới đoạn |
| tiki-seller-warranty-faq.md | FixedSizeChunker (`fixed_size`) | 23 | 598 (min 546 – max 600) | Kém — chunk gần như đều tăm tắp 600 ký tự, tức cắt bừa |
| tiki-seller-warranty-faq.md | SentenceChunker (`by_sentences`) | 46 | 296 (min 110 – max 628) | Khá — nhưng chunk dễ vắt qua hai mục FAQ liền nhau |
| tiki-seller-warranty-faq.md | RecursiveChunker (`recursive`) | 27 | 504 (min 178 – max 599) | Tốt — 27 chunk xấp xỉ số mục FAQ của tài liệu |
| shopee-warranty-buyer.md | FixedSizeChunker (`fixed_size`) | 5 | 590 (min 549 – max 600) | Kém |
| shopee-warranty-buyer.md | SentenceChunker (`by_sentences`) | 9 | 326 (min 134 – max 490) | Khá |
| shopee-warranty-buyer.md | RecursiveChunker (`recursive`) | 7 | 418 (min 297 – max 539) | Tốt |

**Đọc bảng này thế nào.** Cột `min`/`max` tiết lộ nhiều hơn cột trung bình: `fixed_size` trên FAQ Tiki cho min 546 / max 600 — gần như mọi chunk đều chạm trần, nghĩa là nó cắt theo bộ đếm ký tự chứ không theo bất kỳ ranh giới ngữ nghĩa nào. Ngược lại `recursive` có min 178 / max 599, biên độ rộng vì nó *tôn trọng* độ dài tự nhiên của từng đoạn. `by_sentences` cho chunk ngắn nhất (296–326) nên thông tin đặc nhất, nhưng cũng nhiều chunk nhất, tức chi phí embedding cao nhất.

### Chiến lược của từng thành viên

**Thành viên 1 — Ngô Hoàng Thụy Khuê**
- **Loại chiến lược:** Recursive + metadata filter
- **Mô tả & lý do chọn cho chủ đề này:** Chính sách và quy trình bảo hành thường có nhiều tiêu đề con, điều kiện, thời hạn và tab trạng thái. Recursive chunking giúp giữ phần đầu đề và đoạn liên quan gần nhau; bộ lọc `audience` giúp câu hỏi giới hạn đúng phía người mua hay Nhà Bán, giảm nhiễu khi nhiều tài liệu cùng đề cập chủ đề "đổi trả".
- **Code snippet (nếu custom):**
```python
results = store.search_with_filter(
    query,
    top_k=3,
    metadata_filter={"audience": "buyer"}  # hoặc {"audience": "seller"}
)
```

**Thành viên 2 - Hoàng Đức Dũng**
- **Loại chiến lược:** Sentence chunking (`SentenceChunker`, 4 câu/chunk) + audience filter
- **Mô tả & lý do chọn cho chủ đề này:** Cắt theo ranh giới câu thay vì theo số ký tự, vì văn bản chính sách gồm nhiều điều khoản độc lập — mỗi điều khoản thường gói gọn trong 1-3 câu và cắt giữa câu sẽ làm mất một vế điều kiện. Regex `(?<=[.!?])\s+` dùng lookbehind nên giữ lại dấu câu, và phủ được cả `". "` lẫn `".\n"` — cần thiết vì corpus tiếng Việt có nhiều đoạn xuống dòng ngay sau dấu chấm. Kết quả: 104 chunks, dài trung bình 438 ký tự — nhỏ nhất trong ba chiến lược, nên mỗi chunk đặc thông tin hơn.
- **Đóng góp thêm ngoài chiến lược chunking:** xây `bench.py` — công cụ đo dùng chung cho cả nhóm, và đề xuất **cách chấm hai mức** mô tả ở phần Baseline Analysis bên trên.
- **Code snippet (nếu custom):**
```python
class SentenceChunker:
    # Câu kết thúc bằng . ! ? rồi tới khoảng trắng (space hoặc xuống dòng)
    SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")

    def __init__(self, max_sentences_per_chunk: int = 3) -> None:
        # max(1, ...) chặn slice bước 0 gây vòng lặp vô hạn
        self.max_sentences_per_chunk = max(1, max_sentences_per_chunk)

    def chunk(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []
        sentences = [s.strip() for s in self.SENTENCE_BOUNDARY.split(text)]
        sentences = [s for s in sentences if s]
        step = self.max_sentences_per_chunk
        return [" ".join(sentences[i:i + step]) for i in range(0, len(sentences), step)]
```

### So Sánh Giữa Các Thành Viên

> Điểm truy xuất chấm theo `docs/SCORING.md` trên cùng 5 câu hỏi, cùng corpus, cùng embedding `text-embedding-3-small`, `top_k=3` — chỉ khác dòng chọn chunker.

| Thành viên | Chiến lược (Strategy) | Điểm truy xuất (/10) | Điểm mạnh | Điểm yếu |
|-----------|----------|----------------------|-----------|----------|
| Ngô Hoàng Thụy Khuê | Recursive + audience filter | 9/10 | Dễ giữ ngữ cảnh, ít nhầm với chính sách khác | Cần cẩn thận khi câu hỏi có từ khóa chung như "đổi trả" |
| Hoàng Đức Dũng | Sentence (4 câu/chunk) + audience filter | 5/10 (top-1 2/5 · MRR 0.500) | Chunk nhỏ nhất (438 ký tự TB) nên thông tin đặc, không bao giờ cắt giữa câu làm mất vế điều kiện. Thắng ở câu 1 và câu 5 — hai câu mà đáp án gói gọn trong một vài câu văn. | Bỏ qua ranh giới cấu trúc: chunk chỉ đếm đủ 4 câu rồi cắt, bất kể đang ở giữa mục nào. Bằng chứng: chunk chứa đáp án câu 2 (`tiki-seller-warranty-faq#22`) vắt qua **hai mục FAQ** — nửa đầu là "Bước 4" của mục 7, nửa sau mới là mục 8 có đáp án. Embedding của chunk lai hai chủ đề nên không khớp hẳn câu hỏi nào, và trượt cả câu 2 lẫn câu 3. |

**Chiến lược nào tốt nhất cho chủ đề này? Tại sao?**
> **Không chiến lược nào thắng toàn diện — và đó mới là kết luận đáng giá.** Tổng điểm cho thấy `recursive` nhỉnh nhất (6/10, MRR 0.600), `sentence` bám sát (5/10, MRR 0.500), `fixed_size` bỏ xa phía sau (2/10, MRR 0.200). Nhưng chấm từng câu thì bức tranh đảo ngược hẳn:
>
> | Câu | Dạng hỏi | fixed | recursive | sentence |
> |---|---|---|---|---|
> | 1 | hỏi điều kiện | 0/2 | 0/2 | **2/2** |
> | 2 | tra số liệu | 0/2 | **2/2** | 0/2 |
> | 3 | hỏi quy trình | 0/2 | **2/2** | 0/2 |
> | 4 | liệt kê | 0/2 | 0/2 | **1/2** |
> | 5 | cần lọc metadata | **2/2** | **2/2** | **2/2** |
>
> `recursive` và `sentence` **bù trừ nhau gần như hoàn hảo**: recursive thắng đúng hai câu sentence trượt (2, 3), sentence thắng đúng hai câu recursive trượt (1, 4). Lý do nằm ở cấu trúc tài liệu. Recursive cắt ưu tiên ở `\n\n` nên bám ranh giới mục — hợp với câu 2 và 3 vốn hỏi thẳng vào một mục FAQ Tiki. Sentence cho chunk ngắn và đặc thông tin (438 vs 493 ký tự) — hợp với câu 1 và 4 nơi đáp án gói trong vài câu liền nhau giữa một đoạn dài.
>
> `fixed_size` thua ở mọi câu trừ câu 5 vì lý do đã thấy ngay từ bảng baseline: trên FAQ Tiki nó cho min 546 / max 600, tức gần như mọi chunk đều chạm trần — nó cắt theo bộ đếm ký tự, không theo bất kỳ ranh giới ngữ nghĩa nào.
>
> **Kết luận cho hệ thống thật:** không chọn một rồi bỏ phần còn lại, mà **kết hợp hai tầng** — cắt theo cấu trúc trước (heading / `\n\n`), rồi trong mỗi mục dài mới cắt tiếp theo câu, và gắn lại tiêu đề mục vào từng mảnh con. Cách này giữ được cả ưu điểm bám cấu trúc của recursive lẫn mật độ thông tin của sentence.

**Failure case thật đã quan sát:**
> **Câu hỏi hỏng:** câu 4 — *"Sản phẩm cần thỏa những điều kiện nào để được bảo hành miễn phí?"*, chạy với `RecursiveChunker` + filter `audience=buyer`. Kết quả 0/2: chunk chứa gold xếp hạng **7 trên 23** ứng viên, không lọt top-3. Top-1 lại là `shopee-warranty-buyer#2` — mục **"Những trường hợp *không* được bảo hành"**, tức đúng chủ đề nhưng **ngược nghĩa** với câu hỏi.
>
> **Vì sao hỏng — hai nguyên nhân chồng lên nhau.**
> *Thứ nhất, embedding không mã hoá phủ định.* Đo trực tiếp trên `text-embedding-3-small`: cosine giữa "Sản phẩm này được bảo hành" và "Sản phẩm này **không** được bảo hành" là **`+0.8853`** — cao hơn cả cặp thật sự đồng nghĩa "12 tháng" ↔ "một năm" (`+0.6641`). Chữ "không" là token ngắn, tần suất cao, đóng góp rất ít vào vector. Với model, mục "điều kiện được bảo hành" và mục "trường hợp không được bảo hành" gần như là một.
> *Thứ hai, đáp án bị pha loãng trong chunk.* Chunk chứa gold (`shopee-warranty-buyer#0`) mở đầu bằng tiêu đề tài liệu và đoạn phạm vi áp dụng — một danh sách dài tên thương hiệu: *"Samsung Official Store, Apple Flagship Store, LG Official Store, Electrolux, Philips, Viettel Store, FPTShop..."*. Câu "hội đủ các điều kiện sau" nằm ở cuối chunk. Embedding của cả chunk bị danh sách thương hiệu chi phối nên không giống câu hỏi về điều kiện bảo hành.
>
> **Đề xuất sửa, theo thứ tự ưu tiên:**
> 1. **Chunk theo heading.** Cắt tại mỗi dòng `## `, mỗi mục thành một chunk mang đúng tiêu đề của nó. Riêng câu 4 sẽ được giải quyết: "## 1. Điều kiện bảo hành" tách khỏi "## 2. Những trường hợp không được bảo hành", và cũng tách khỏi đoạn phạm vi áp dụng đầu tài liệu.
> 2. **Bỏ phần mở đầu tài liệu** (tiêu đề + phạm vi áp dụng) trước khi chunk — rẻ nhất, vá được nguyên nhân thứ hai.
> 3. **Thêm `overlap` cho `RecursiveChunker`.** Hiện nó cắt không chồng lấn nên mỗi thông tin chỉ có đúng một cơ hội lọt top-3.
> 4. Với vấn đề phủ định thì chunking không giải quyết được — cần rerank hoặc để LLM đọc nhiều chunk hơn rồi tự loại mục ngược nghĩa.

**Lưu ý về embedding backend:**
> Toàn bộ số đo trong báo cáo này chạy trên **embedding thật** — `OpenAIEmbedder` (`text-embedding-3-small`) — nên score số là đáng tin và so sánh được giữa các chiến lược. Agent dùng `gpt-4o-mini`, `top_k=3`.
>
> Nhóm **đã** thử `MockEmbedder` ở giai đoạn đầu và ghi lại để đối chiếu: nó băm MD5 chuỗi rồi sinh số giả ngẫu nhiên nên hoàn toàn không mang ngữ nghĩa. Bằng chứng: câu hỏi "Chunking là gì?" cho top-1 là `rag_system_design.md` (score 0.150) trong khi `chunking_experiment_report.md` — file đúng chủ đề — xếp thứ ba với 0.025. Nếu buộc phải dùng mock, mọi kết luận về thứ hạng top-k đều vô nghĩa và phần phân tích phải chuyển sang các chỉ số không phụ thuộc embedding: `count`, `avg_length`, độ mạch lạc của chunk.
>
> Một cái bẫy đã gặp thật và đáng cảnh báo: `main.py` nuốt exception khi khởi tạo embedder và âm thầm rơi về mock. Nhóm từng chạy với `.env` đặt `EMBEDDING_PROVIDER=openai` nhưng chưa cài gói `openai`, và không hề biết mình đang đo bằng mock. Vì vậy `bench.py` được viết để **cảnh báo to** khi rơi về mock thay vì im lặng.

---

## 3. Câu hỏi đánh giá & Chất lượng truy xuất (Retrieval Quality) — Nhóm (10 điểm)

### Câu hỏi đánh giá & Câu trả lời chuẩn (nhóm thống nhất)

> **Đúng 5 câu hỏi**, đa dạng, có thể kiểm chứng; **ít nhất 1 câu** cần lọc metadata mới trả lời tốt. Đây là bộ câu hỏi chung cho mọi thành viên chạy.

| # | Câu hỏi (Query) | Câu trả lời chuẩn (Gold Answer) | Chunk nào chứa thông tin? |
|---|-------|-------------------------------|--------------------------|
| 1 | Theo chính sách Hoàng Hà Mobile, khách hàng được đổi mới miễn phí trong thời gian nào? | Trong 15 hoặc 30 ngày đầu kể từ ngày mua, tùy theo dòng sản phẩm, nếu sản phẩm được xác nhận lỗi phần cứng do nhà sản xuất thì được đổi mới miễn phí 100%. | `hoanghamobile-warranty-buyer.md`, mục "a) Trong 15 hoặc 30 ngày đầu kể từ ngày mua" |
| 2 | Trong mô hình Seller Center, Nhà Bán có bao nhiêu ngày làm việc để xác nhận phương án xử lý yêu cầu đổi trả? | 02 ngày làm việc kể từ khi mã yêu cầu ghi nhận trạng thái "Cần Nhà Bán phản hồi". | `tiki-seller-warranty-faq.md`, mục 8 "Nhà Bán có thời gian bao lâu để xác nhận yêu cầu đổi, trả, bảo hành?" |
| 3 | Nếu Nhà Bán không phản hồi, Tiki sẽ xử lý yêu cầu của Khách Hàng như thế nào? | Tiki sẽ hoàn tiền cho Khách Hàng và không chịu trách nhiệm trong trường hợp Nhà Bán không hoặc không thể thu hồi hàng hóa; số tiền hoàn trả được cấn trừ vào kỳ thanh toán tiếp theo của Nhà Bán. | `tiki-seller-warranty-faq.md`, **mục 6** "Nếu Nhà Bán không phản hồi..." — *không phải* mục 4 (xem ghi chú bên dưới) |
| 4 | Sản phẩm cần thỏa những điều kiện nào để được bảo hành miễn phí? | Lỗi kỹ thuật do nhà sản xuất; còn trong thời hạn bảo hành; có hóa đơn điện tử hoặc mã đơn hàng; với hàng điện gia dụng thì phiếu/tem bảo hành và tem niêm phong còn nguyên vẹn. | `shopee-warranty-buyer.md`, mục 1 "Điều kiện bảo hành" |
| 5 | Thời gian bảo hành tối đa là bao lâu? *(câu cần lọc metadata)* | **Phía seller:** Nhà Bán cam kết tối đa không quá 30 ngày. **Phía buyer:** 12 tháng máy mới (Hoàng Hà) / 20–45 ngày làm việc (Shopee). | `tiki-seller-warranty-faq.md`, mục 5 "Thời gian Nhà Bán cam kết bảo hành là bao lâu?" |

### Tổng hợp chất lượng truy xuất của nhóm

> Cách chấm (theo `docs/SCORING.md`): **2 điểm/câu** — top-3 chứa chunk liên quan + agent trả lời đúng (2), có liên quan nhưng thiếu/không ở top-1 (1), không có trong top-3 (0).

| # | Câu hỏi | Chiến lược tốt nhất cho câu này | Có chunk liên quan trong top-3? | Ghi chú |
|---|---------|-------------------------------|-------------------------------|---------|
| 1 | Theo chính sách Hoàng Hà Mobile, khách hàng được đổi mới miễn phí trong thời gian nào? | **Sentence** (2/2) | Có — chỉ với sentence | fixed 0/2, recursive 0/2. Recursive lấy nhầm mục *bảo hành* thay vì mục *đổi mới 15/30 ngày*; chunk gold xếp hạng 6/23. |
| 2 | Trong mô hình Seller Center, Nhà Bán có bao nhiêu ngày làm việc để xác nhận phương án xử lý yêu cầu đổi trả? | **Recursive** (2/2) | Có — chỉ với recursive | fixed 0/2, sentence 0/2. Chunk sentence chứa đáp án (`#22`) vắt qua hai mục FAQ nên embedding lai chủ đề, tụt xuống hạng 12/50. |
| 3 | Nếu Nhà Bán không phản hồi, Tiki sẽ xử lý yêu cầu của Khách Hàng như thế nào? | **Recursive** (2/2) | Có — chỉ với recursive | sentence lấy nhầm mục *Nhà Bán từ chối* thay vì mục *không phản hồi*; chunk gold hạng 14/50. |
| 4 | Sản phẩm cần thỏa những điều kiện nào để được bảo hành miễn phí? | **Sentence** (1/2, hạng 2) | Một phần | fixed 0/2, recursive 0/2. Cả ba đều bị mục *"những trường hợp **không** được bảo hành"* chiếm top-1 — xem failure case ở mục 2. |
| 5 | Thời gian bảo hành tối đa là bao lâu? | **Cả ba đều 2/2** | Có | Câu duy nhất mọi chiến lược đều đạt. Nhưng chỉ đạt **khi có** `metadata_filter` — xem bảng A/B bên dưới. |

**Lọc bằng metadata có giúp ích không? Ở câu hỏi nào?**
> **Có, nhưng chỉ ở đúng một câu — và đó là điều đáng nói.** Chạy A/B thật (bảng dưới) trên cả 5 câu: **4/5 câu cho kết quả y hệt nhau dù có lọc hay không**. Lý do là chúng tự phân biệt bằng từ vựng — "Hoàng Hà Mobile" chỉ có trong tài liệu buyer, "Nhà Bán"/"Seller Center" chỉ có trong tài liệu seller — nên embedding đã tách đúng, filter thành thừa.
>
> **Câu 5 là câu duy nhất filter thực sự quyết định đúng/sai:** *"Thời gian bảo hành tối đa là bao lâu?"* không nêu người hỏi là ai, trong khi hai phía corpus cùng nói về thời hạn bảo hành bằng cùng từ vựng nhưng cho đáp án khác nhau — buyer: 12 tháng máy mới / 20–45 ngày làm việc; seller: tối đa 30 ngày. Không lọc thì top-3 lẫn cả hai phía và agent trả lời sai đối tượng.
>
> **Bài học quan trọng hơn cả câu trả lời:** một câu hỏi đã chứa từ khóa đặc trưng của một phía thì **không chứng minh được gì** về giá trị của metadata filter. Muốn đo tác dụng của filter, phải cố tình viết câu hỏi *mơ hồ về đối tượng*. Bộ 5 câu đầu tiên của nhóm không có câu nào như vậy, chạy A/B ra kết quả giống hệt nhau ở cả 5 câu, và nhóm đã phải thay câu 5 để có bằng chứng.

### A/B kiểm chứng filter `audience` (bắt buộc)

| Câu hỏi | Với filter | Không filter | Kết luận |
|---|---|---|---|
| **Câu 5** — "Thời gian bảo hành tối đa là bao lâu?" *(không nêu đối tượng)* | `faq#4`, `faq#14`, `faq#17` — **cả 3 đều seller** → **2/2** | `faq#4`, `hoanghamobile#1`, `shopee#4` — **2/3 slot bị buyer chiếm** → 2/2 | **KHÁC NHAU.** Top-1 vẫn đúng nên điểm không đổi, nhưng ngữ cảnh đưa vào agent thì lẫn cả "12 tháng máy mới" (buyer) lẫn "tối đa 30 ngày" (seller) — đủ để agent trả lời sai đối tượng. Đây là bằng chứng chính. |
| Câu 1 — "Theo chính sách **Hoàng Hà Mobile**, khách hàng được đổi mới miễn phí..." | `hoanghamobile#10`, `hoanghamobile#0`, `hoanghamobile#3` | `hoanghamobile#10`, `hoanghamobile#0`, `hoanghamobile#3` | **GIỐNG HỆT.** Tên "Hoàng Hà Mobile" chỉ xuất hiện ở tài liệu buyer nên embedding tự tách được. |
| Câu 2, 3, 4 — đều chứa "**Nhà Bán**" / "Seller Center" hoặc hỏi về chính sách buyer | (xem `ket_qua_benchmark.txt`) | Trùng với cột bên trái | **GIỐNG HỆT** ở cả ba câu. Filter không thay đổi gì. |

> **Kết luận:** filter `audience` **không phải lúc nào cũng cần** — nó chỉ tạo khác biệt khi câu hỏi mơ hồ về đối tượng, tức khi embedding một mình không đủ để phân biệt. Nhưng đúng vào những lúc đó thì nó là thứ **duy nhất** cứu được câu trả lời, vì `audience` là thông tin nằm ở metadata chứ không nằm trong ngữ nghĩa câu văn. Ba chiến lược chunking khác nhau đều cho kết quả A/B khác nhau ở câu 5, xác nhận đây là đặc tính của câu hỏi chứ không phải của cách chunk.

---

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

**Những phân tích (insights) hay nhất nhóm sẽ trình bày:**
> **1. Embedding không mã hoá phủ định.** Đo trên `text-embedding-3-small`: cosine giữa "Sản phẩm này **được** bảo hành" và "Sản phẩm này **không** được bảo hành" là `+0.8853` — **cao hơn** cả cặp thật sự đồng nghĩa "12 tháng" ↔ "một năm" (`+0.6641`). Hệ quả đã xảy ra thật trong benchmark: câu 4 hỏi *điều kiện được* bảo hành nhưng top-1 là mục *"những trường hợp không được bảo hành"*.
>
> **2. Chấm ở mức `doc_id` thổi phồng kết quả.** Cùng một lần chạy, chấm "tài liệu gold có trong top-3 không" cho **5/5 ở cả ba chiến lược** — bảng so sánh trở nên vô dụng. Chuyển sang chấm mức nội dung (chunk phải chứa một chuỗi đặc trưng trích nguyên văn từ tài liệu) thì điểm tụt xuống 2/10 – 6/10 và ba chiến lược mới tách nhau ra. **Chênh lệch giữa hai cách chấm chính là phát hiện đáng giá nhất của buổi lab.**
>
> **3. Không chiến lược chunking nào thắng toàn diện.** `recursive` và `sentence` bù trừ nhau gần như hoàn hảo: recursive thắng đúng hai câu sentence trượt, sentence thắng đúng hai câu recursive trượt. Tổng điểm che mất điều này — chỉ chấm từng câu mới thấy.
>
> **4. Retrieval trượt mà agent vẫn trả lời đúng.** Ở câu 2 với chiến lược sentence, chunk chứa đáp án xếp hạng 12/50 và không lọt top-3, nhưng agent vẫn trả lời đúng nhờ các chunk lân cận nhắc tới cùng mốc "02 ngày làm việc". Lần này là may — lần khác chunk lân cận có thể chứa con số của một điều khoản khác và agent sẽ bịa ra đáp án sai mà vẫn trôi chảy. Bài học: **đừng đánh giá hệ thống RAG chỉ bằng câu trả lời cuối cùng.**

**Bài học rút ra khi so sánh trong nhóm:**
> Cùng corpus, cùng 5 câu hỏi, cùng embedding, chỉ khác **một dòng chọn chunker** — kết quả chênh nhau gấp ba: `fixed_size` 2/10, `sentence` 5/10, `recursive` 6/10. Việc ép cả nhóm chạy chung một công cụ đo (`bench.py`) và chỉ được đổi đúng dòng đó là quyết định quan trọng nhất về mặt phương pháp; nếu mỗi người tự viết script riêng thì ba con số này không so sánh được với nhau.
>
> Nhưng bài học lớn nhất lại đi ngược trực giác ban đầu của nhóm: **chọn chiến lược tốt nhất là câu hỏi sai**. Recursive và sentence bù trừ nhau gần như hoàn hảo trên 5 câu, mỗi bên thắng đúng hai câu bên kia trượt. Điều đó nói rằng cách chia nhỏ văn bản nên phụ thuộc vào **cấu trúc tài liệu**, chứ không phải chọn một lần rồi áp cho mọi thứ.
>
> Một bài học thực tế nữa: nhóm suýt ghi số nhiễu vào báo cáo vì `main.py` âm thầm rơi về `MockEmbedder` khi thiếu gói `openai`. Công cụ đo phải **la lớn khi nó đang đo sai**, chứ không được im lặng.

**Nếu làm lại, nhóm sẽ thay đổi gì trong chiến lược dữ liệu (data strategy)?**
> **1. Chunk theo heading, và gắn lại tiêu đề vào từng mảnh con.** Đây là thay đổi có tác động lớn nhất. Văn bản quy định đã được người soạn chia sẵn thành mục (`## 1. Điều kiện bảo hành`), mỗi mục là một đơn vị ngữ nghĩa trọn vẹn — vậy mà cả ba chiến lược hiện tại đều phớt lờ cấu trúc đó. Nó giải quyết trực tiếp failure case ở mục 2, nơi mục *'điều kiện được bảo hành'* bị dính chung chunk với đoạn phạm vi áp dụng đầy tên thương hiệu.
>
> **2. Viết câu hỏi đánh giá *trước*, rồi mới thiết kế chunking.** Nhóm làm ngược lại và trả giá: bộ 5 câu đầu tiên không có câu nào thực sự cần `metadata_filter`, chạy A/B ra kết quả giống hệt nhau ở cả 5 câu, phải viết lại. Câu hỏi đánh giá xác định cái mình đang tối ưu — chọn sau thì chỉ là hợp thức hoá kết quả đã có.
>
> **3. Đối chiếu gold answer với đúng câu chữ của câu hỏi.** Nhóm từng chấm oan một câu 0/2 vì gold trỏ nhầm vào mục 4 trong khi câu hỏi dùng chữ của mục 6 — hai điều khoản khác điều kiện kích hoạt và khác hậu quả. Retrieval hoàn toàn đúng, chỉ gold sai. Với corpus quy định có nhiều điều khoản gần giống nhau, **chấm tự động chỉ đáng tin bằng chất lượng của gold**.
>
> **4. Thêm `overlap` cho chunker.** Hiện mỗi thông tin chỉ có đúng một cơ hội lọt top-3; nếu nó nằm gần ranh giới chunk thì coi như mất.

---

## Tự Đánh Giá (Phần Nhóm)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Lựa chọn tài liệu (Document Set Quality) | 10 / 10 |
| Thiết kế chiến lược (Strategy Design) | 14 / 15 |
| Chất lượng truy xuất (Retrieval Quality) | 8 / 10 |
| Thuyết trình (Demo) | 5 / 5 |
| **Tổng phần nhóm** | **37 / 40** |

> **Tự đánh giá trung thực, không cho điểm tối đa.**
> *Thiết kế chiến lược 14/15:* ba chiến lược được đo trên cùng một khung công bằng, có baseline số thật và phân tích được lý do thắng/thua của từng câu. Trừ 1 điểm vì nhóm **chưa hiện thực hoá chunker theo heading** — hướng đã xác định rõ là tốt nhất cho corpus có cấu trúc mục như thế này, nhưng mới dừng ở đề xuất.
> *Chất lượng truy xuất 8/10:* chấm theo thang `docs/SCORING.md` ở mức nội dung, điểm thô tốt nhất là 6/10 (`recursive`). Trừ 2 điểm vì 2/5 câu vẫn không đưa được chunk gold vào top-3 ở bất kỳ chiến lược nào.