# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** [Tên nhóm]
**Thành viên:** [Họ tên từng thành viên]
**Ngày:** [Ngày nộp]

> **Nộp 1 bản / nhóm.** Phần cá nhân (hướng tiếp cận, kết quả riêng, dự đoán…) mỗi thành viên nộp riêng trong `REPORT_CANHAN.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần nhóm: 40** = Lựa chọn tài liệu (10) + Thiết kế chiến lược (15) + Chất lượng truy xuất (10) + Thuyết trình (5).

---

## 1. Lựa chọn tài liệu (Document Set Quality) — Nhóm (10 điểm)

### Chủ đề (Domain) & Lý Do Chọn

**Chủ đề:** Chính sách **bảo hành** trên nền tảng thương mại điện tử Việt Nam — nhìn từ **hai phía**: người mua (buyer) và nhà bán hàng (seller).

**Tại sao nhóm chọn chủ đề này?**
> Bảo hành là chủ đề mà cùng một khái niệm ("thời gian bảo hành", "hạn phản hồi") lại có **con số khác nhau tùy đối tượng đọc**: người mua thấy "12 tháng máy mới / 20–45 ngày làm việc", còn nhà bán hàng bị ràng buộc "cam kết tối đa 30 ngày, phản hồi trong 02 ngày làm việc". Đây chính là tình huống mà tìm kiếm ngữ nghĩa thuần túy sẽ trộn lẫn hai đáp án, buộc phải dùng `metadata_filter={"audience": ...}` mới trả lời đúng. Ngoài ra toàn bộ nguồn đều là trang chính sách công khai, không chứa dữ liệu cá nhân, phù hợp yêu cầu quản trị dữ liệu của lab.

### Danh sách tài liệu (Data Inventory)

| # | Tên tài liệu | Nguồn (Source URL) | Ngày lấy / Phiên bản | Số ký tự | Metadata đã gán |
|---|--------------|------------|--------------------|----------|-----------------|
| 1 | Chính sách bảo hành Hoàng Hà Mobile dành cho khách mua | https://hoanghamobile.com/chinh-sach-bao-hanh | 2026-09-20 / áp dụng từ 29-09-2025 | 8.255 | `audience=buyer`, `category=warranty-policy`, `language=vi` |
| 2 | Chính sách bảo hành cho sản phẩm mua tại Shopee | https://help.shopee.vn/portal/4/article/79046 | 2026-09-20 / not-stated | 3.210 | `audience=buyer`, `category=warranty-policy`, `language=vi` |
| 3 | Câu hỏi thường gặp về xử lý đổi trả bảo hành cho Nhà Bán Hàng (Tiki) | https://hocvien.tiki.vn/faq/cau-hoi-thuong-gap-ve-xu-ly-doi-tra-bao-hanh/ | 2026-09-20 / not-stated | 14.054 | `audience=seller`, `category=warranty-process`, `language=vi` |
| 4 | Quy trình xử lý đổi/trả/bảo hành — mô hình Dropship (Tiki) | https://hocvien.tiki.vn/faq/huong-dan-quy-trinh-xu-ly-doi-tra-bao-hanh-mo-hinh-dropship/ | 2026-09-20 / not-stated | 11.148 | `audience=seller`, `category=warranty-process`, `language=vi` |
| 5 | Quy trình xử lý đổi/trả/bảo hành — mô hình SD (Tiki) | https://hocvien.tiki.vn/faq/huong-dan-quy-trinh-xu-ly-doi-tra-bao-hanh-mo-hinh-sd/ | 2026-09-20 / not-stated | 7.430 | `audience=seller`, `category=warranty-process`, `language=vi` |
| 6 | Quy trình xử lý đổi/trả/bảo hành — mô hình FBT (Tiki) | https://hocvien.tiki.vn/faq/mo-hinh-fbt-huong-dan-quy-trinh-xu-ly-doi-tra-bao-hanh/ | 2026-09-20 / not-stated | 3.518 | `audience=seller`, `category=warranty-process`, `language=vi` |

**Tổng:** 6 tài liệu · 47.615 ký tự · phân bố `audience`: buyer 2 / seller 4.

**Ghi chú về tính minh bạch nguồn:**
- Một URL ứng viên (`fptshop.com.vn/ho-tro/chinh-sach-bao-hanh`) bị **`robots.txt` của FPT Shop chặn**. Crawler báo `disallowed by robots.txt` và bỏ qua; nhóm **không dùng công cụ khác để lách** và loại URL này khỏi corpus.
- `cellphones.com.vn/chinh-sach-bao-hanh` bị loại sau khi kiểm tra: trang chỉ là danh mục logo hãng, không chứa điều khoản bảo hành nào.
- Chỉ tài liệu #1 nêu mốc hiệu lực trên trang gốc ("Áp dụng từ ngày 29/09/2025") nên được ghi vào `document_version`; 5 tài liệu còn lại để `not-stated`, **không suy đoán số hiệu**.
- Toàn bộ output thô đã được làm sạch thủ công trước khi lưu (xoá menu, footer, danh sách gian hàng, bảng giá thu cũ đổi mới không liên quan). Ví dụ tài liệu #1 giảm từ ~19 KB xuống 8,3 KB.

**Danh sách kiểm tra quản trị dữ liệu (Data governance checklist):**
- [x] Tập tài liệu (Corpus) chỉ chứa nguồn công khai/được phép dùng và không chứa dữ liệu cá nhân, thông tin đăng nhập hoặc tài liệu nội bộ.
- [x] Mỗi tài liệu có `source_url`, `retrieved_at`, `document_version` (hoặc ngày hiệu lực) trong metadata.

### Cấu trúc Metadata (Metadata Schema)

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho truy xuất (retrieval)? |
|----------------|------|---------------|-------------------------------|
| `doc_id` | string | `tiki-seller-warranty-faq` | Khoá định danh duy nhất, trùng tên file — dùng để truy vết chunk về tài liệu gốc khi chấm gold answer. |
| `audience` | enum (`buyer` \| `seller`) | `buyer` | **Trường lọc chính.** Cùng câu hỏi "bảo hành bao lâu?" cho hai đáp án khác nhau; `metadata_filter={"audience":"buyer"}` loại bỏ 4 tài liệu phía seller khỏi top-k. |
| `category` | enum (`warranty-policy` \| `warranty-process`) | `warranty-process` | Tách *điều khoản quyền lợi* khỏi *quy trình vận hành*, giúp câu hỏi dạng "các bước xử lý" không bị chunk điều khoản lấn chỗ. |
| `source_url` | string (URL) | `https://help.shopee.vn/portal/4/article/79046` | Trích dẫn nguồn trong câu trả lời, cho phép người đọc tự kiểm chứng. |
| `retrieved_at` | date (ISO) | `2026-09-20` | Chính sách TMĐT thay đổi thường xuyên; cho biết dữ liệu cũ tới mức nào. |
| `document_version` | string | `ap-dung-tu-2025-09-29` / `not-stated` | Phân biệt phiên bản hiệu lực khi hai bản chính sách cùng tồn tại; `not-stated` ghi rõ là trang gốc không nêu, tránh bịa. |
| `language` | ISO 639-1 | `vi` | Toàn bộ corpus tiếng Việt; giữ trường này để sẵn sàng mở rộng đa ngữ mà không phải đổi schema. |

---

## 2. Thiết kế chiến lược (Strategy Design) — Nhóm (15 điểm)

> Mỗi thành viên thử **một chiến lược khác nhau** trên cùng bộ tài liệu; nhóm tổng hợp và so sánh ở đây.

### Phân tích đường cơ sở (Baseline Analysis)

Chạy `ChunkingStrategyComparator().compare()` trên 2-3 tài liệu:

| Tài liệu | Chiến lược (Strategy) | Số lượng Chunk | Độ dài trung bình | Giữ được ngữ cảnh không? |
|-----------|----------|-------------|------------|-------------------|
| | FixedSizeChunker (`fixed_size`) | | | |
| | SentenceChunker (`by_sentences`) | | | |
| | RecursiveChunker (`recursive`) | | | |

### Chiến lược của từng thành viên

> Mỗi thành viên điền một khối dưới đây (copy thêm nếu nhóm có nhiều hơn 3 người).

**Thành viên 1 — [Tên]**
- **Loại chiến lược:** [FixedSize / Sentence / Recursive / custom]
- **Mô tả & lý do chọn cho chủ đề này:** *(2-3 câu)*
- **Code snippet (nếu custom):**
```python
# Dán mã nguồn (implementation) vào đây
```

**Thành viên 2 — [Tên]**
- **Loại chiến lược:**
- **Mô tả & lý do chọn:**
- **Code snippet (nếu custom):**

**Thành viên 3 — [Tên]**
- **Loại chiến lược:**
- **Mô tả & lý do chọn:**
- **Code snippet (nếu custom):**

### So Sánh Giữa Các Thành Viên

| Thành viên | Chiến lược (Strategy) | Điểm truy xuất (/10) | Điểm mạnh | Điểm yếu |
|-----------|----------|----------------------|-----------|----------|
| | | | | |
| | | | | |
| | | | | |

**Chiến lược nào tốt nhất cho chủ đề này? Tại sao?**
> *Viết 2-3 câu — đây là phần được đánh giá cao nhất (khả năng suy nghĩ & giải thích):*

---

## 3. Câu hỏi đánh giá & Chất lượng truy xuất (Retrieval Quality) — Nhóm (10 điểm)

### Câu hỏi đánh giá & Câu trả lời chuẩn (nhóm thống nhất)

> **Đúng 5 câu hỏi**, đa dạng, có thể kiểm chứng; **ít nhất 1 câu** cần lọc metadata mới trả lời tốt. Đây là bộ câu hỏi chung cho mọi thành viên chạy.

| # | Câu hỏi (Query) | Câu trả lời chuẩn (Gold Answer) | Chunk nào chứa thông tin? |
|---|-------|-------------------------------|--------------------------|
| 1 | | | |
| 2 | | | |
| 3 | | | |
| 4 | | | |
| 5 | | | |

### Tổng hợp chất lượng truy xuất của nhóm

> Cách chấm (theo `docs/SCORING.md`): **2 điểm/câu** — top-3 chứa chunk liên quan + agent trả lời đúng (2), có liên quan nhưng thiếu/không ở top-1 (1), không có trong top-3 (0).

| # | Câu hỏi | Chiến lược tốt nhất cho câu này | Có chunk liên quan trong top-3? | Ghi chú |
|---|---------|-------------------------------|-------------------------------|---------|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |
| 4 | | | | |
| 5 | | | | |

**Lọc bằng metadata có giúp ích không? Ở câu hỏi nào?**
> *Viết 2-3 câu:*

---

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

**Những phân tích (insights) hay nhất nhóm sẽ trình bày:**
> *Liệt kê 2-3 ý:*

**Bài học rút ra khi so sánh trong nhóm:**
> *Viết 2-3 câu — cùng tài liệu nhưng chiến lược khác nhau dẫn tới khác biệt gì?*

**Nếu làm lại, nhóm sẽ thay đổi gì trong chiến lược dữ liệu (data strategy)?**
> *Viết 2-3 câu:*

---

## Tự Đánh Giá (Phần Nhóm)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Lựa chọn tài liệu (Document Set Quality) | / 10 |
| Thiết kế chiến lược (Strategy Design) | / 15 |
| Chất lượng truy xuất (Retrieval Quality) | / 10 |
| Thuyết trình (Demo) | / 5 |
| **Tổng phần nhóm** | **/ 40** |
