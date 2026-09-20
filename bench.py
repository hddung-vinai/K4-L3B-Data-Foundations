"""
Retrieval benchmark for the warranty corpus.

This is a measurement tool, not a graded exercise — no test suite covers it.

Run:
    python bench.py                      # default strategy
    python bench.py --strategy sentence  # compare another chunker
    python bench.py --compare            # run every strategy back to back

Every member runs the SAME queries on the SAME corpus and changes only the
chunking strategy, so the numbers stay comparable.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from pathlib import Path
from typing import Any, Callable

import yaml
from dotenv import load_dotenv

from src.agent import KnowledgeBaseAgent
from src.chunking import FixedSizeChunker, RecursiveChunker, SentenceChunker
from src.embeddings import (
    EMBEDDING_PROVIDER_ENV,
    GEMINI_EMBEDDING_MODEL,
    LOCAL_EMBEDDING_MODEL,
    OPENAI_EMBEDDING_MODEL,
    GeminiEmbedder,
    LocalEmbedder,
    OpenAIEmbedder,
    _mock_embed,
)
from src.models import Document
from src.store import EmbeddingStore

CORPUS_DIR = Path("data/warranty")
CHUNK_SIZE = 600
TOP_K = 3

# ---------------------------------------------------------------------------
# ĐỔI ĐÚNG MỘT DÒNG NÀY sang chiến lược của bạn. Mọi thứ khác giữ nguyên để
# so sánh giữa các thành viên còn công bằng.
STRATEGY = "sentence"
# ---------------------------------------------------------------------------

STRATEGIES: dict[str, Callable[[], Any]] = {
    "fixed": lambda: FixedSizeChunker(chunk_size=CHUNK_SIZE, overlap=50),
    "sentence": lambda: SentenceChunker(max_sentences_per_chunk=4),
    "recursive": lambda: RecursiveChunker(chunk_size=CHUNK_SIZE),
}


# ---------------------------------------------------------------------------
# Bộ câu hỏi đánh giá
#
# BẢN NHÁP — R2 chủ trì chốt bản cuối, cả nhóm dùng chung đúng 5 câu này và
# đồng bộ với bảng ở REPORT_NHOM mục 3. Gold answer bên dưới đều trích được
# từ tài liệu, không suy đoán chính sách nền tảng.
#
# Câu 5 là câu cần metadata_filter: "bảo hành bao lâu" không nêu người hỏi là
# ai, mà phía buyer trả lời "12 tháng máy mới" còn phía seller là "tối đa 30
# ngày". Không lọc thì top-k lẫn cả hai và agent trả lời sai đối tượng.
# ---------------------------------------------------------------------------
# QUERIES: list[dict[str, Any]] = [
#     {
#         "id": 1,
#         "question": "Máy mới mua được bảo hành trong bao lâu?",
#         "kind": "tra số liệu",
#         "gold": "Máy mới: 12 tháng hoặc theo quy định của hãng; máy cũ: lên đến 6 tháng.",
#         "gold_phrase": "máy mới: 12 tháng hoặc theo quy định của hãng",
#         "expect_doc_id": "hoanghamobile-warranty-buyer",
#         "filter": {"audience": "buyer"},
#     },
#     {
#         "id": 2,
#         "question": "Sản phẩm không được bảo hành trong những trường hợp nào?",
#         "kind": "hỏi điều kiện",
#         "gold": "Các trường hợp loại trừ nêu trong mục điều kiện bảo hành của chính sách.",
#         "gold_phrase": "Vi phạm một trong những điều kiện bảo hành miễn phí",
#         "expect_doc_id": "shopee-warranty-buyer",
#         "filter": {"audience": "buyer"},
#     },
#     {
#         "id": 3,
#         "question": "Nhà Bán phải phản hồi yêu cầu đổi trả trong bao nhiêu ngày làm việc?",
#         "kind": "tra số liệu",
#         "gold": "02 ngày làm việc kể từ khi yêu cầu đổi, trả, bảo hành được tạo.",
#         "gold_phrase": "không xác nhận phương án xử lý trong 02 ngày làm việc",
#         "expect_doc_id": "tiki-seller-warranty-faq",
#         "filter": {"audience": "seller"},
#     },
#     {
#         "id": 4,
#         "question": "Quy trình xử lý đổi trả bảo hành theo mô hình Dropship gồm những bước nào?",
#         "kind": "hỏi quy trình",
#         "gold": "Chuỗi bước từ khi yêu cầu được tạo đến khi Tiki trả hàng về cho Nhà Bán.",
#         "gold_phrase": "Bước 1: Tiki tiếp nhận, kiểm tra yêu cầu đổi/trả/bảo hành",
#         "expect_doc_id": "tiki-seller-warranty-dropship",
#         "filter": {"audience": "seller"},
#     },
#     {
#         "id": 5,
#         "question": "Thời gian bảo hành tối đa là bao lâu?",
#         "kind": "câu cần lọc metadata",
#         "gold": "Phía seller: Nhà Bán cam kết tối đa không quá 30 ngày. "
#                 "Phía buyer: 12 tháng với máy mới (Hoàng Hà) / 20-45 ngày làm việc (Shopee).",
#         "gold_phrase": "tối đa không quá 30 ngày",
#         "expect_doc_id": "tiki-seller-warranty-faq",
#         "filter": {"audience": "seller"},
#         # Câu này chạy hai lần (có lọc / không lọc) để thấy filter đổi kết quả ra sao.
#         "demo_filter_effect": True,
#     },
# ]

BENCHMARK_QUERIES = [
    {
        "id": 1,
        "kind": "hỏi điều kiện",
        "query": "Theo chính sách Hoàng Hà Mobile, khách hàng được đổi mới miễn phí trong thời gian nào?",
        "metadata_filter": {"audience": "buyer"},
        "gold": "Trong 15 hoặc 30 ngày đầu kể từ ngày mua, tùy theo dòng sản phẩm, nếu sản phẩm được xác nhận lỗi phần cứng do nhà sản xuất thì được đổi mới miễn phí 100%.",
        "gold_phrase": "Đổi mới miễn phí 100% nếu sản phẩm được xác nhận lỗi phần cứng do nhà sản xuất",
        "expect_doc_id": "hoanghamobile-warranty-buyer",
    },
    {
        "id": 2,
        "kind": "tra số liệu",
        "query": "Trong mô hình Seller Center, Nhà Bán có bao nhiêu ngày làm việc để xác nhận phương án xử lý yêu cầu đổi trả?",
        "metadata_filter": {"audience": "seller"},
        "gold": "Nhà Bán có 02 ngày làm việc kể từ khi sản phẩm được cập nhật trạng thái cần Nhà Bán phản hồi để xác nhận phương án xử lý yêu cầu đổi, trả, bảo hành.",
        "gold_phrase": "02 ngày làm việc kể từ khi mã yêu cầu ghi nhận",
        "expect_doc_id": "tiki-seller-warranty-faq",
    },
    {
        "id": 3,
        "kind": "hỏi quy trình",
        "query": "Nếu Nhà Bán không phản hồi, Tiki sẽ xử lý yêu cầu của Khách Hàng như thế nào?",
        "metadata_filter": {"audience": "seller"},
        # Gold lấy từ FAQ mục 6 (dòng 54), KHÔNG phải mục 4 (dòng 40).
        # Hai mục dễ lẫn nhưng khác điều kiện kích hoạt và khác hậu quả:
        #   mục 4 = Nhà Bán không XÁC NHẬN PHƯƠNG ÁN trong 02 ngày -> Tiki chủ động xử lý
        #   mục 6 = Nhà Bán KHÔNG PHẢN HỒI               -> Tiki hoàn tiền, cấn trừ kỳ sau
        # Câu hỏi dùng chữ "không phản hồi" nên gold phải là mục 6.
        # (Bản gốc của R2 ghép cả vế "bồi thường" từ dòng 36/82 — điều khoản bảo
        #  hành quá hạn, khác ngữ cảnh hẳn — nên đã bỏ.)
        "gold": "Tiki sẽ hoàn tiền cho Khách Hàng và không chịu trách nhiệm trong trường hợp Nhà Bán không "
                "hoặc không thể thu hồi hàng hóa; số tiền hoàn trả được cấn trừ vào kỳ thanh toán tiếp theo của Nhà Bán.",
        "gold_phrase": "Tiki sẽ hoàn tiền cho Khách Hàng và không chịu trách nhiệm",
        "expect_doc_id": "tiki-seller-warranty-faq",
    },
    {
        "id": 4,
        "kind": "liệt kê",
        # Thay câu "Nhà Bán xác nhận ... qua đâu trong hệ thống?": câu đó trùng
        # chủ đề với câu 2 và 3 (đều là seller + xác nhận yêu cầu đổi trả), và
        # bộ 5 câu đang thiếu hẳn dạng liệt kê.
        "query": "Sản phẩm cần thỏa những điều kiện nào để được bảo hành miễn phí?",
        "metadata_filter": {"audience": "buyer"},
        "gold": "Lỗi kỹ thuật do nhà sản xuất; còn trong thời hạn bảo hành; có hóa đơn điện tử hoặc mã đơn hàng; "
                "với hàng điện gia dụng thì phiếu/tem bảo hành và tem niêm phong còn nguyên vẹn.",
        "gold_phrase": "Sản phẩm được bảo hành miễn phí nếu sản phẩm đó hội đủ các điều kiện sau",
        "expect_doc_id": "shopee-warranty-buyer",
    },
    {
        "id": 5,
        "kind": "câu cần lọc metadata",
        # Câu hỏi KHÔNG nêu người hỏi là ai, trong khi cả hai phía corpus đều nói
        # về thời hạn bảo hành bằng cùng từ vựng nhưng cho đáp án khác nhau:
        #   buyer  -> 12 tháng máy mới (Hoàng Hà) / 20-45 ngày làm việc (Shopee)
        #   seller -> Nhà Bán cam kết tối đa không quá 30 ngày
        # Không lọc thì top-3 lẫn cả hai và agent trả lời sai đối tượng.
        # Thay câu "Theo quy trình đổi mới của Hoàng Hà Mobile...": câu đó nêu
        # đích danh Hoàng Hà nên embedding tự tách được, filter thành thừa.
        "query": "Thời gian bảo hành tối đa là bao lâu?",
        "metadata_filter": {"audience": "seller"},
        "gold": "Nhà Bán cam kết thời gian bảo hành tối đa không quá 30 ngày, tính từ khi Nhà Bán nhận được hàng "
                "đến khi bảo hành xong, không tính thời gian vận chuyển.",
        "gold_phrase": "tối đa không quá 30 ngày",
        "expect_doc_id": "tiki-seller-warranty-faq",
        # Chạy hai lần (có lọc / không lọc) để lấy bằng chứng cho mục 3 REPORT_NHOM.
        "demo_filter_effect": True,
    },
]


def split_frontmatter(raw: str) -> tuple[dict[str, Any], str]:
    """
    Split a "---\\n...\\n---\\n" YAML header off the body.

    Bỏ frontmatter trước khi chunk, nếu không là đang đo cả khối YAML 9 dòng
    chứ không phải nội dung chính sách.
    """
    if not raw.startswith("---"):
        return {}, raw

    parts = raw.split("---", 2)
    if len(parts) < 3:
        return {}, raw

    try:
        metadata = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError as exc:
        print(f"  ! frontmatter không parse được, bỏ qua: {exc}")
        return {}, parts[2].lstrip("\n")

    if not isinstance(metadata, dict):
        return {}, parts[2].lstrip("\n")
    return metadata, parts[2].lstrip("\n")


def load_chunked_documents(corpus_dir: Path, chunker: Any) -> list[Document]:
    """
    Read every .md file, strip frontmatter, chunk the body, emit one Document
    per chunk with the frontmatter spread into its metadata.

    Chunking xảy ra ở ĐÂY, ngoài store. Nạp cả file làm một Document thì
    retrieval trả về nguyên file — vô dụng cho việc trích gold answer.
    """
    documents: list[Document] = []
    files = sorted(corpus_dir.glob("*.md"))
    if not files:
        print(f"Không tìm thấy file .md nào trong {corpus_dir}")
        return documents

    for path in files:
        frontmatter, body = split_frontmatter(path.read_text(encoding="utf-8"))
        chunks = chunker.chunk(body)
        # doc_id trỏ về tên file gốc; Document.id mới là "file#0".
        doc_id = str(frontmatter.get("doc_id") or path.stem)

        for index, chunk in enumerate(chunks):
            documents.append(
                Document(
                    id=f"{path.stem}#{index}",
                    content=chunk,
                    metadata={
                        # Trải frontmatter vào MỌI chunk, nếu không
                        # search_with_filter không có gì để lọc.
                        **frontmatter,
                        "doc_id": doc_id,
                        "source": str(path),
                        "chunk_index": index,
                        "chunk_count": len(chunks),
                    },
                )
            )

        audience = frontmatter.get("audience", "?")
        print(f"  {path.name:<42} {len(chunks):>3} chunks  audience={audience}")

    return documents


def build_embedder() -> Callable[[str], list[float]]:
    """Pick a backend from EMBEDDING_PROVIDER, with a content-hash cache on top."""
    load_dotenv(override=False)
    provider = os.getenv(EMBEDDING_PROVIDER_ENV, "mock").strip().lower()

    builders: dict[str, Callable[[], Any]] = {
        "local": lambda: LocalEmbedder(model_name=os.getenv("LOCAL_EMBEDDING_MODEL", LOCAL_EMBEDDING_MODEL)),
        "openai": lambda: OpenAIEmbedder(model_name=os.getenv("OPENAI_EMBEDDING_MODEL", OPENAI_EMBEDDING_MODEL)),
        "gemini": lambda: GeminiEmbedder(model_name=os.getenv("GEMINI_EMBEDDING_MODEL", GEMINI_EMBEDDING_MODEL)),
    }

    backend: Any = _mock_embed
    if provider in builders:
        try:
            backend = builders[provider]()
        except Exception as exc:
            # main.py nuốt lỗi này và âm thầm dùng mock — ở công cụ đo thì im
            # lặng là tệ nhất: bạn sẽ ghi số nhiễu vào báo cáo mà không biết.
            print(f"!! EMBEDDING_PROVIDER={provider} không khởi tạo được: {exc}")
            print("!! Rơi về MockEmbedder — điểm số dưới đây là NHIỄU NGẪU NHIÊN, đừng dùng cho báo cáo.")

    name = getattr(backend, "_backend_name", backend.__class__.__name__)
    print(f"Embedding backend: {name}")

    # Cache theo hash nội dung: chạy lại bench nhiều lần với cùng chunk thì
    # không gọi API lần nữa. Với provider tính tiền, đây là tiền thật.
    cache: dict[str, list[float]] = {}

    def embed(text: str) -> list[float]:
        key = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if key not in cache:
            cache[key] = backend(text)
        return cache[key]

    embed.cache = cache  # type: ignore[attr-defined]
    return embed


def build_llm() -> Callable[[str], str]:
    """
    LLM dùng cho cột "câu trả lời của Agent".

    Ưu tiên OpenAI chat (cùng key với embedding, model rẻ). Không gọi được thì
    lùi về bản rút trích: trả lại chính ngữ cảnh, đủ để đối chiếu gold answer
    bằng mắt nhưng KHÔNG phải câu trả lời do mô hình sinh — có cảnh báo rõ.
    """
    model = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
    try:
        from openai import OpenAI

        client = OpenAI()

        def ask(prompt: str) -> str:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            return (response.choices[0].message.content or "").strip()

        print(f"LLM backend: {model}")
        return ask
    except Exception as exc:
        print(f"!! Không dựng được LLM ({exc}); cột 'Agent' sẽ là trích ngữ cảnh, không phải câu trả lời sinh ra.")

        def extract(prompt: str) -> str:
            _, _, context = prompt.partition("NGỮ CẢNH:")
            context, _, _ = context.partition("CÂU HỎI:")
            return "[TRÍCH NGỮ CẢNH] " + " ".join(context.split())[:300]

        return extract


def preview(text: str, width: int = 90) -> str:
    flat = " ".join(text.split())
    return flat[:width] + ("..." if len(flat) > width else "")


def normalize(text: str) -> str:
    """Collapse whitespace so a gold phrase survives chunking's line breaks."""
    return " ".join(text.split())


def is_relevant(hit: dict[str, Any], query: dict[str, Any]) -> bool:
    """
    Decide whether one retrieved chunk actually answers the query.

    Chấm bằng gold_phrase — một đoạn chữ chính xác trích từ tài liệu — chứ
    không chỉ so doc_id. Lý do: so ở mức tài liệu thì chiến lược nào cũng lấy
    được *một chunk nào đó* từ đúng file, nên cả ba cùng đạt 100% và bảng so
    sánh vô nghĩa. Ngược lại, chunker cắt ngang câu chứa gold_phrase sẽ trượt
    — đúng thứ ta muốn đo.

    Không so chunk id được, vì ranh giới chunk khác nhau giữa các chiến lược.
    """
    if hit["metadata"].get("doc_id") != query["expect_doc_id"]:
        return False
    gold_phrase = query.get("gold_phrase")
    if not gold_phrase:
        return True  # chưa khai báo gold_phrase thì lùi về chấm mức tài liệu
    return normalize(gold_phrase) in normalize(hit["content"])


def score_hits(hits: list[dict[str, Any]], query: dict[str, Any]) -> tuple[int, int]:
    """
    Score one query against docs/SCORING.md and return (points, rank).

    Thang điểm: 2 nếu chunk liên quan đứng top-1, 1 nếu có trong top-3 nhưng
    không phải top-1, 0 nếu vắng mặt. rank = 0 nghĩa là không tìm thấy.
    """
    for rank, hit in enumerate(hits, start=1):
        if is_relevant(hit, query):
            return (2 if rank == 1 else 1), rank
    return 0, 0


def print_hits(hits: list[dict[str, Any]], query: dict[str, Any], indent: str = "    ") -> None:
    """Print top-k, marking every hit that counts as relevant."""
    if not hits:
        print(f"{indent}(không có kết quả)")
        return

    for rank, hit in enumerate(hits, start=1):
        metadata = hit["metadata"]
        label = f"{metadata.get('doc_id', '?')}#{metadata.get('chunk_index')}"
        mark = "✓" if is_relevant(hit, query) else " "
        print(f"{indent}{mark} {rank}. score={hit['score']:+.4f}  {label}")
        print(f"{indent}     {preview(hit['content'])}")


def run_benchmark(strategy_name: str) -> dict[str, Any]:
    chunker = STRATEGIES[strategy_name]()

    print("=" * 78)
    print(f"CHIẾN LƯỢC: {strategy_name}  (chunk_size={CHUNK_SIZE}, top_k={TOP_K})")
    print("=" * 78)

    print(f"\nNạp corpus từ {CORPUS_DIR}/")
    docs = load_chunked_documents(CORPUS_DIR, chunker)
    if not docs:
        return {"strategy": strategy_name, "hit_rate": 0.0, "chunks": 0}

    lengths = [len(doc.content) for doc in docs]
    print(f"\nTổng: {len(docs)} chunks · độ dài trung bình {sum(lengths) / len(lengths):.0f} ký tự "
          f"(min {min(lengths)}, max {max(lengths)})")

    store = EmbeddingStore(collection_name=f"bench_{strategy_name}", embedding_fn=build_embedder())
    store.add_documents(docs)

    agent = KnowledgeBaseAgent(store=store, llm_fn=build_llm())

    points = 0
    top1 = 0
    reciprocal_ranks: list[float] = []
    rows: list[dict[str, Any]] = []
    ab_rows: list[dict[str, Any]] = []

    for query in BENCHMARK_QUERIES:
        print(f"\n--- Câu {query['id']} [{query['kind']}] ---")
        print(f"Q: {query['query']}")
        print(f"Gold: {query['gold']}")
        print(f"Kỳ vọng: {query['expect_doc_id']}  |  filter={query['metadata_filter']}")

        results = store.search_with_filter(
            query["query"], top_k=TOP_K, metadata_filter=query["metadata_filter"]
        )
        print("  Có lọc metadata:")
        print_hits(results, query)

        earned, rank = score_hits(results, query)
        points += earned
        top1 += 1 if rank == 1 else 0
        reciprocal_ranks.append(1 / rank if rank else 0.0)
        print(f"    -> {earned}/2 điểm (hạng {rank or '-'})")

        # SCORING.md đòi "top-3 có chunk liên quan VÀ agent trả lời đúng", nên
        # phải gọi agent chứ không chỉ đo retrieval.
        answer = agent.answer(query["query"], top_k=TOP_K)
        print(f"  Agent: {preview(answer, 140)}")

        top_hit = results[0] if results else None
        rows.append({
            "id": query["id"],
            "kind": query["kind"],
            "query": query["query"],
            "top1_chunk": preview(top_hit["content"], 70) if top_hit else "(không có)",
            "top1_id": (f"{top_hit['metadata'].get('doc_id')}#{top_hit['metadata'].get('chunk_index')}"
                        if top_hit else "-"),
            "score": top_hit["score"] if top_hit else 0.0,
            "points": earned,
            "rank": rank,
            "answer": preview(answer, 90),
        })

        if query.get("demo_filter_effect"):
            unfiltered = store.search(query["query"], top_k=TOP_K)
            print("  KHÔNG lọc (để đối chiếu):")
            print_hits(unfiltered, query)
            ab_rows.append({
                "strategy": strategy_name,
                "id": query["id"],
                "with": [f"{h['metadata'].get('doc_id')}#{h['metadata'].get('chunk_index')}" for h in results],
                "without": [f"{h['metadata'].get('doc_id')}#{h['metadata'].get('chunk_index')}" for h in unfiltered],
                "with_points": earned,
                "without_points": score_hits(unfiltered, query)[0],
            })

    max_points = 2 * len(BENCHMARK_QUERIES)
    mrr = sum(reciprocal_ranks) / len(BENCHMARK_QUERIES)
    print(f"\n>>> {strategy_name}: {points}/{max_points} điểm · top-1 {top1}/{len(BENCHMARK_QUERIES)} "
          f"· MRR {mrr:.3f}\n")

    return {
        "strategy": strategy_name,
        "chunks": len(docs),
        "avg_length": sum(lengths) / len(lengths),
        "points": points,
        "top1": top1,
        "mrr": mrr,
        "rows": rows,
        "ab_rows": ab_rows,
    }


class Tee:
    """Ghi song song ra terminal và ra ket_qua_benchmark.txt."""

    def __init__(self, stream: Any, path: Path) -> None:
        self.stream = stream
        self.file = path.open("w", encoding="utf-8")

    def write(self, data: str) -> int:
        self.stream.write(data)
        self.file.write(data)
        return len(data)

    def flush(self) -> None:
        self.stream.flush()
        self.file.flush()

    def close(self) -> None:
        self.file.close()


def print_report_tables(summaries: list[dict[str, Any]]) -> None:
    """In các bảng dán thẳng được vào REPORT_CANHAN mục 5 / REPORT_NHOM mục 2."""
    max_points = 2 * len(BENCHMARK_QUERIES)

    if len(summaries) > 1:
        print("\n" + "=" * 78)
        print("BẢNG SO SÁNH CHIẾN LƯỢC  (REPORT_NHOM mục 2)")
        print("=" * 78)
        print(f"{'Chiến lược':<12} {'Chunks':>7} {'Dài TB':>8} {'Điểm':>8} {'Top-1':>7} {'MRR':>7}")
        print("-" * 78)
        for row in summaries:
            print(f"{row['strategy']:<12} {row['chunks']:>7} {row['avg_length']:>8.0f} "
                  f"{str(row['points']) + '/' + str(max_points):>8} "
                  f"{str(row['top1']) + '/' + str(len(BENCHMARK_QUERIES)):>7} {row['mrr']:>7.3f}")

    for summary in summaries:
        print("\n" + "=" * 78)
        print(f"KẾT QUẢ TRUY XUẤT — {summary['strategy']}  (REPORT_CANHAN mục 5)")
        print("=" * 78)
        print("| # | Câu hỏi | Top-1 chunk | Score | Liên quan? | Câu trả lời của Agent |")
        print("|---|---------|-------------|-------|-----------|----------------------|")
        for row in summary["rows"]:
            relevant = {2: "Có (top-1)", 1: f"Có (hạng {row['rank']})", 0: "Không"}[row["points"]]
            print(f"| {row['id']} | {row['query']} | {row['top1_id']}: {row['top1_chunk']} "
                  f"| {row['score']:+.4f} | {relevant} — {row['points']}/2 | {row['answer']} |")

    ab_rows = [row for summary in summaries for row in summary["ab_rows"]]
    if ab_rows:
        print("\n" + "=" * 78)
        print("A/B METADATA FILTER  (REPORT_NHOM mục 3)")
        print("=" * 78)
        for row in ab_rows:
            same = "GIỐNG NHAU — câu hỏi chưa thực sự cần filter" if row["with"] == row["without"] else "KHÁC NHAU"
            print(f"\n[{row['strategy']}] câu {row['id']} — {same}")
            print(f"  có lọc   ({row['with_points']}/2): {row['with']}")
            print(f"  KHÔNG lọc ({row['without_points']}/2): {row['without']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strategy", choices=sorted(STRATEGIES), default=STRATEGY)
    parser.add_argument("--compare", action="store_true", help="chạy lần lượt mọi chiến lược")
    parser.add_argument("--out", default="ket_qua_benchmark.txt", help="file ghi kết quả")
    args = parser.parse_args()

    if not CORPUS_DIR.is_dir():
        print(f"Không thấy thư mục corpus: {CORPUS_DIR.resolve()}")
        return 1

    tee = Tee(sys.stdout, Path(args.out))
    original_stdout = sys.stdout
    sys.stdout = tee  # type: ignore[assignment]
    try:
        names = sorted(STRATEGIES) if args.compare else [args.strategy]
        summaries = [run_benchmark(name) for name in names]
        print_report_tables(summaries)
    finally:
        sys.stdout = original_stdout
        tee.close()

    print(f"\nĐã ghi kết quả vào {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
