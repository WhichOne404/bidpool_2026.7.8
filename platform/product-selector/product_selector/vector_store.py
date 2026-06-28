"""向量检索模块 - 语义搜索辅助产品匹配

使用 FAISS + sentence-transformers 进行语义搜索。
当关键词匹配失败时，作为 fallback 推断产品类别。

依赖（可选）:
  - faiss-cpu: FAISS 向量索引
  - sentence-transformers: 文本嵌入模型

如果依赖不可用，优雅降级为关键词匹配。
"""
from typing import List, Optional, Tuple
import numpy as np

from product_selector.models import Product

# 模型配置
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
VECTOR_DIM = 384  # all-MiniLM-L6-v2 输出维度


class ProductVectorStore:
    """产品向量存储，支持语义搜索"""

    def __init__(self):
        self._index = None
        self._products: List[Product] = []
        self._embeddings: Optional[np.ndarray] = None
        self._available = False
        self._model = None

    @property
    def available(self) -> bool:
        """检查向量检索是否可用"""
        return self._available

    def build_index(self, products: List[Product]) -> None:
        """从产品列表构建 FAISS 索引

        每个产品生成一条嵌入文本，包含名称、描述和关键特性。
        """
        self._products = products
        if not products:
            return

        try:
            self._model = self._load_model()
            texts = [_product_to_text(p) for p in products]
            embeddings = self._model.encode(texts, show_progress_bar=False)
            self._embeddings = np.array(embeddings, dtype=np.float32)

            self._build_faiss_index()
            self._available = True
        except ImportError:
            self._available = False
        except Exception:
            self._available = False

    def search(
        self, query: str, top_k: int = 5,
    ) -> List[Tuple[Product, float]]:
        """语义搜索，返回最匹配的产品及相似度分数

        Args:
            query: 搜索查询文本
            top_k: 返回结果数量

        Returns:
            [(product, similarity_score), ...] 按相似度降序排列
        """
        if not self._available or not self._products:
            return []

        try:
            query_embedding = np.array(
                self._model.encode([query], show_progress_bar=False),
                dtype=np.float32,
            )

            # FAISS 搜索
            if self._index is not None:
                distances, indices = self._index.search(query_embedding, top_k)
                results: List[Tuple[Product, float]] = []
                for i in range(len(indices[0])):
                    idx = indices[0][i]
                    if idx >= 0 and idx < len(self._products):
                        # 将 L2 距离转换为相似度 [0, 1]
                        dist = distances[0][i]
                        sim = 1.0 / (1.0 + dist)
                        results.append((self._products[idx], sim))
                return results

            # 回退: 直接用 numpy 计算余弦相似度
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
        """从查询文本推断最可能的产品类别"""
        results = self.search(query, top_k=1)
        if results:
            product, score = results[0]
            if score > 0.3:  # 相似度阈值
                return product.category.value
        return None

    def _load_model(self):
        """加载嵌入模型，未缓存时跳过以避免阻塞下载"""
        import os
        from sentence_transformers import SentenceTransformer

        # 检查模型是否已缓存，避免打开下载
        cache_dir = os.path.join(
            os.path.expanduser("~"),
            ".cache", "huggingface", "hub",
            "models--sentence-transformers--all-MiniLM-L6-v2",
        )
        if not os.path.isdir(cache_dir):
            raise FileNotFoundError(
                f"Embedding model {EMBEDDING_MODEL} not cached at {cache_dir}"
            )

        return SentenceTransformer(EMBEDDING_MODEL)

    def _build_faiss_index(self) -> None:
        """构建 FAISS 索引"""
        try:
            import faiss
            dim = self._embeddings.shape[1]
            index = faiss.IndexFlatL2(dim)
            index.add(self._embeddings)
            self._index = index
        except ImportError:
            self._index = None


def _product_to_text(product: Product) -> str:
    """将产品转换为索引文本"""
    parts = [f"{product.name}"]
    if product.description:
        parts.append(product.description)
    if product.key_features:
        parts.append(" ".join(product.key_features))
    # 添加类别信息以提升匹配精度
    category_names = {
        "WAF": "Web应用防火墙 WAF",
        "host_security": "主机安全 HIDS 服务器安全",
        "vuln_scanner": "漏洞扫描 漏洞评估",
        "deception": "蜜罐 诱捕 欺骗防御",
        "ndr": "流量分析 NDR 网络检测",
        "api_security": "API安全 接口安全",
        "code_security": "代码安全 SAST 静态分析 代码审计",
        "asset": "资产管理 安全运营 SOC 态势感知",
    }
    extra = category_names.get(product.category.value, "")
    if extra:
        parts.append(extra)
    return " ".join(parts)
