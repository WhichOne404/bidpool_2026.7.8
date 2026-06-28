"""API Embedding 向量存储 - 使用 API 生成 embedding 替代本地模型

与 ProductVectorStore 接口一致，供 agent.py 透明切换。
"""
from typing import List, Optional, Tuple
import numpy as np

from product_selector.models import Product
from product_selector.llm_client import LLMClient
from product_selector.vector_store import _product_to_text


class APIEmbeddingStore:
    """使用 API 生成 embedding 的向量存储"""

    def __init__(self, embedding_client: LLMClient):
        self._client = embedding_client
        self._index = None
        self._products: List[Product] = []
        self._embeddings: Optional[np.ndarray] = None

    @property
    def available(self) -> bool:
        return self._client is not None and self._client.available

    def build_index(self, products: List[Product]) -> None:
        self._products = products
        if not products or not self.available:
            return

        try:
            texts = [_product_to_text(p) for p in products]
            all_embeddings: List[List[float]] = []
            batch_size = 20

            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                vecs = self._client.embed(batch)
                if vecs is None:
                    return
                all_embeddings.extend(vecs)

            self._embeddings = np.array(all_embeddings, dtype=np.float32)
            self._build_faiss_index()
        except Exception:
            pass

    def search(
        self, query: str, top_k: int = 5,
    ) -> List[Tuple[Product, float]]:
        if not self.available or not self._embeddings is not None:
            return []
        if not self._products:
            return []

        try:
            query_vecs = self._client.embed([query])
            if query_vecs is None:
                return []
            query_embedding = np.array(query_vecs, dtype=np.float32)

            if self._index is not None:
                distances, indices = self._index.search(query_embedding, top_k)
                results = []
                for i in range(len(indices[0])):
                    idx = indices[0][i]
                    if 0 <= idx < len(self._products):
                        dist = distances[0][i]
                        sim = 1.0 / (1.0 + dist)
                        results.append((self._products[idx], sim))
                return results

            # numpy 余弦相似度 fallback
            if self._embeddings is not None:
                query_norm = query_embedding / (
                    np.linalg.norm(query_embedding) + 1e-8
                )
                emb_norm = self._embeddings / (
                    np.linalg.norm(self._embeddings, axis=1, keepdims=True) + 1e-8
                )
                scores = np.dot(query_norm, emb_norm.T)
                top_indices = np.argsort(scores)[::-1][:top_k]
                return [
                    (self._products[i], float(scores[i]))
                    for i in top_indices
                ]
        except Exception:
            pass

        return []

    def find_category(self, query: str) -> Optional[str]:
        results = self.search(query, top_k=1)
        if results:
            _, score = results[0]
            if score > 0.3:
                return results[0][0].category.value
        return None

    def _build_faiss_index(self) -> None:
        try:
            import faiss
            dim = self._embeddings.shape[1]
            index = faiss.IndexFlatL2(dim)
            index.add(self._embeddings)
            self._index = index
        except ImportError:
            self._index = None
