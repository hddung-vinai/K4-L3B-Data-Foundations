from typing import Callable

from .store import EmbeddingStore


class KnowledgeBaseAgent:
    """
    An agent that answers questions using a vector knowledge base.

    Retrieval-augmented generation (RAG) pattern:
        1. Retrieve top-k relevant chunks from the store.
        2. Build a prompt with the chunks as context.
        3. Call the LLM to generate an answer.
    """

    NO_CONTEXT_MESSAGE = "Không tìm thấy thông tin liên quan trong cơ sở tri thức."

    PROMPT_TEMPLATE = """Bạn là trợ lý trả lời câu hỏi dựa trên ngữ cảnh được cung cấp.

Quy tắc:
- Chỉ dùng thông tin trong phần NGỮ CẢNH bên dưới.
- Nếu ngữ cảnh không đủ để trả lời, hãy nói rõ là không tìm thấy thông tin.
- Trích dẫn nguồn theo số [1], [2]... tương ứng với đoạn ngữ cảnh đã dùng.

NGỮ CẢNH:
{context}

CÂU HỎI: {question}

TRẢ LỜI:"""

    def __init__(self, store: EmbeddingStore, llm_fn: Callable[[str], str]) -> None:
        self.store = store
        self.llm_fn = llm_fn

    def _build_context(self, chunks: list[dict]) -> str:
        """Đánh số từng chunk kèm nguồn để câu trả lời có thể trích dẫn lại."""
        blocks = []
        for index, chunk in enumerate(chunks, start=1):
            source = chunk.get("metadata", {}).get("source", chunk.get("metadata", {}).get("doc_id", "unknown"))
            blocks.append(f"[{index}] (nguồn: {source})\n{chunk['content']}")
        return "\n\n".join(blocks)

    def answer(self, question: str, top_k: int = 3) -> str:
        chunks = self.store.search(question, top_k=top_k)
        if not chunks:
            return self.NO_CONTEXT_MESSAGE

        prompt = self.PROMPT_TEMPLATE.format(
            context=self._build_context(chunks),
            question=question,
        )
        response = self.llm_fn(prompt)
        return response if isinstance(response, str) else str(response)
