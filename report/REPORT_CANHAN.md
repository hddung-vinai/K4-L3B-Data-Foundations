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
> Vì cosine bỏ qua độ lớn vector, chỉ so hướng. Độ lớn thường phản ánh độ dài văn bản chứ không phản ánh nghĩa, nên hai đoạn cùng chủ đề nhưng chênh lệch độ dài sẽ có Euclid lớn trong khi góc vẫn nhỏ. Ngoài ra ở số chiều cao, khoảng cách Euclid giữa mọi cặp điểm có xu hướng co về gần nhau nên kém phân biệt

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
> *Viết 2-3 câu: dùng biểu thức chính quy (regex) gì để phát hiện câu? Xử lý trường hợp ngoại lệ (edge case) nào?*

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:
> *Viết 2-3 câu: thuật toán hoạt động thế nào? Base case (trường hợp cơ sở) là gì?*

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:
> *Viết 2-3 câu: lưu trữ thế nào? Tính độ tương tự ra sao?*

**`search_with_filter` + `delete_document`** — hướng tiếp cận:
> *Viết 2-3 câu: lọc (filter) trước hay sau? Xóa bằng cách nào?*

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:
> *Viết 2-3 câu: cấu trúc prompt? Cách đưa ngữ cảnh (inject context) vào thế nào?*

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```
# Dán kết quả (output) của: pytest tests/ -v
```

**Số lượng bài test vượt qua (pass):** __ / 42

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | | | cao / thấp | | |
| 2 | | | cao / thấp | | |
| 3 | | | cao / thấp | | |
| 4 | | | cao / thấp | | |
| 5 | | | cao / thấp | | |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**
> *Viết 2-3 câu:*

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá của nhóm** trên mã nguồn cá nhân của bạn trong gói `src`. **5 câu hỏi này phải trùng với các thành viên cùng nhóm** (xem `REPORT_NHOM.md`).

| # | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Điểm Score | Có liên quan không? (Relevant) | Câu trả lời của Agent (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |
| 4 | | | | | |
| 5 | | | | | |

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** __ / 5

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**
> *Viết 2-3 câu:*

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Khởi động (Warm-up) | / 5 |
| Hướng tiếp cận của tôi (My Approach) | / 10 |
| Hoàn thiện code (Core Implementation — tests) | / 30 |
| Dự đoán độ tương tự (Similarity Predictions) | / 5 |
| Kết quả truy xuất của tôi (Competition Results) | / 10 |
| **Tổng phần cá nhân** | **/ 60** |
