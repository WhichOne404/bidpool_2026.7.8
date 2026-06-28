"""Agent 核心 - 串联意图理解、推理选型，提供统一接口

支持单轮和多轮对话(session管理)。
"""
from typing import List, Dict, Any, Optional
from decimal import Decimal
from dataclasses import dataclass, field
from product_selector.models import (
    Product, UserRequirements, ProductCategory,
    RecommendationResult, ProductConfig, Module,
)
from product_selector.parser import parse_all_products, get_cached_products
from product_selector.intent import extract_requirements
from product_selector.reasoning import recommend, get_optional_module_groups
from product_selector.config import SelectorConfig
from product_selector.vector_store import ProductVectorStore
from product_selector.llm_client import LLMClient, LLMClientConfig


@dataclass
class SessionState:
    """会话状态，跟踪多轮对话中的累积需求"""
    session_id: str
    accumulated_requirements: UserRequirements = field(
        default_factory=UserRequirements,
    )
    conversation_history: List[Dict[str, str]] = field(default_factory=list)


class ProductSelectorAgent:
    """安全产品智能选型 Agent"""

    def __init__(self, data_dir: str = "data", config: Optional[SelectorConfig] = None):
        self.config = config or SelectorConfig(data_dir=data_dir)
        self.products: List[Product] = get_cached_products(
            data_dir, ttl_seconds=self.config.cache_ttl_seconds,
        )
        self._sessions: Dict[str, SessionState] = {}
        self._vector_store: Optional[ProductVectorStore] = None
        self._vector_store_attempted = False
        self._llm_client: Optional[LLMClient] = None
        self._llm_attempted = False
        self._embedding_client: Optional[LLMClient] = None
        self._emb_attempted = False

    def _get_llm_client(self) -> Optional[LLMClient]:
        """懒加载 LLM 客户端"""
        if self._llm_attempted:
            return self._llm_client
        self._llm_attempted = True
        if not self.config.llm_api_base or not self.config.llm_api_key:
            return None
        self._llm_client = LLMClient(LLMClientConfig(
            api_base=self.config.llm_api_base,
            api_key=self.config.llm_api_key,
            model=self.config.llm_model,
        ))
        return self._llm_client if self._llm_client.available else None

    def _get_embedding_client(self) -> Optional[LLMClient]:
        """懒加载 Embedding 客户端"""
        if self._emb_attempted:
            return self._embedding_client
        self._emb_attempted = True
        emb_base = self.config.embedding_api_base or self.config.llm_api_base
        emb_key = self.config.embedding_api_key or self.config.llm_api_key
        if not emb_base or not emb_key:
            return None
        self._embedding_client = LLMClient(LLMClientConfig(
            api_base=emb_base,
            api_key=emb_key,
            model=self.config.embedding_model,
        ))
        return self._embedding_client if self._embedding_client.available else None

    def _get_vector_store(self) -> Optional[ProductVectorStore]:
        """懒加载向量存储，优先使用 API embedding"""
        if not self.config.enable_vector_search:
            return None
        if self._vector_store_attempted:
            return self._vector_store
        self._vector_store_attempted = True
        try:
            # 优先使用 API-based embedding
            from product_selector.api_embedding_store import APIEmbeddingStore
            emb_client = self._get_embedding_client()
            if emb_client and emb_client.available:
                store = APIEmbeddingStore(emb_client)
            else:
                store = ProductVectorStore()
            store.build_index(self.products)
            self._vector_store = store
        except Exception:
            self._vector_store = None
        return self._vector_store

    def get_products_by_category(self, category: str) -> List[Product]:
        try:
            cat = ProductCategory(category)
        except ValueError:
            return []
        return [p for p in self.products if p.category == cat]

    def get_product_by_name(self, name: str) -> Optional[Product]:
        for p in self.products:
            if name in p.name:
                return p
        return None

    def get_versions_for_category(
        self, category: ProductCategory, version_type: str = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """获取指定产品类别的可用版本列表

        Args:
            category: 产品类别
            version_type: 版本类型过滤 ('software' 或 'hardware')

        Returns:
            Dict with 'software' and 'hardware' version lists
        """
        from product_selector.reasoning import filter_valid_versions

        products = self.get_products_by_category(category.value)
        if not products:
            return {"software": [], "hardware": []}

        product = products[0]
        software_versions = filter_valid_versions(product.software_versions, "software")
        hardware_versions = filter_valid_versions(product.hardware_versions, "hardware")

        def _format_version(v):
            return {
                "name": v.name,
                "version_id": v.version_id,
                "version_type": v.version_type,
                "base_price": str(v.get_base_price()),
            }

        return {
            "software": [_format_version(v) for v in software_versions],
            "hardware": [_format_version(v) for v in hardware_versions],
        }

    def process(self, user_input: str) -> Dict[str, Any]:
        """处理用户输入，返回推荐结果或追问（单轮）"""
        requirements = self._extract_requirements_enhanced(user_input)

        # 向量检索 fallback: 关键词无法匹配产品类型时尝试语义搜索
        vs = self._get_vector_store()
        if not requirements._has_product_spec() and vs and vs.available:
            inferred = vs.find_category(user_input)
            if inferred:
                try:
                    requirements.product_category = ProductCategory(inferred)
                except ValueError:
                    pass

        if not requirements.is_complete():
            missing = requirements.missing_fields()
            question = self._build_question(requirements, missing)
            return {
                "type": "question",
                "question": question,
                "missing_fields": missing,
                "requirements": requirements.model_dump(mode="json"),
            }

        result = recommend(self.products, requirements)

        if result is None:
            return {
                "type": "question",
                "question": "抱歉，未找到匹配的产品方案。请提供更多需求信息（如产品类型、性能需求等）。",
                "missing_fields": ["产品类型/性能需求"],
            }

        return {
            "type": "recommendation",
            "data": self._serialize_result(result),
        }

    def _extract_requirements_enhanced(self, user_input: str) -> UserRequirements:
        """增强意图提取：LLM 补充关键词无法提取的信息"""
        requirements = extract_requirements(user_input)

        llm_client = self._get_llm_client()
        if llm_client and llm_client.available:
            try:
                from product_selector.enhanced_intent import extract_requirements_with_llm
                llm_req = extract_requirements_with_llm(user_input, llm_client)
                if llm_req:
                    requirements = _merge_llm_requirements(requirements, llm_req)
            except Exception:
                pass

        return requirements

    def process_with_session(
        self, user_input: str, session_id: str = "default",
    ) -> Dict[str, Any]:
        """带 session 管理的多轮对话处理

        每轮输入的新需求会与已累积的需求合并。
        如果需求仍不完整，返回追问；完整则给出推荐。
        """
        session = self._sessions.get(session_id)
        if session is None:
            session = SessionState(session_id=session_id)
            self._sessions[session_id] = session

        session.conversation_history.append({"role": "user", "content": user_input})

        new_req = self._extract_requirements_enhanced(user_input)

        # 向量检索 fallback
        vs = self._get_vector_store()
        if not new_req._has_product_spec() and vs and vs.available:
            inferred = vs.find_category(user_input)
            if inferred:
                try:
                    new_req.product_category = ProductCategory(inferred)
                except ValueError:
                    pass

        merged = _merge_requirements(session.accumulated_requirements, new_req)
        session.accumulated_requirements = merged

        if not merged.is_complete():
            question = self._get_next_question(merged)
            session.conversation_history.append({"role": "agent", "content": question})
            return {
                "type": "question",
                "question": question,
                "missing_fields": merged.missing_fields(),
                "session_id": session_id,
            }

        result = recommend(self.products, merged)

        if result is None:
            question = "抱歉，未找到匹配的产品方案。请尝试调整需求或提供更多信息。"
            session.conversation_history.append({"role": "agent", "content": question})
            return {
                "type": "question",
                "question": question,
                "missing_fields": [],
                "session_id": session_id,
            }

        session.conversation_history.append({
            "role": "agent",
            "content": result.summary,
        })
        return {
            "type": "recommendation",
            "data": self._serialize_result(result),
            "session_id": session_id,
        }

    def clear_session(self, session_id: str) -> None:
        """清除指定 session"""
        self._sessions.pop(session_id, None)

    def _get_next_question(self, requirements: UserRequirements) -> str:
        """按优先级返回下一个追问"""
        if not requirements._has_product_spec():
            return (
                "请告诉我您需要哪种安全产品？可选类型：\n"
                "• WAF/雷池 - Web应用防火墙\n"
                "• 牧云 - 主机安全\n"
                "• 洞鉴 - 漏洞扫描\n"
                "• 谛听 - 蜜罐诱捕\n"
                "• 全悉 - 流量分析(NDR)\n"
                "• API安全\n"
                "• 慧鉴/码力 - 代码安全\n"
                "• 云图/万象 - 资产管理"
            )

        if not requirements._has_performance_requirement():
            cat = requirements.product_category
            hints: Dict[Optional[ProductCategory], str] = {
                ProductCategory.WAF: "需要防护多少QPS？",
                ProductCategory.HOST_SECURITY: "需要管理多少台服务器/节点？",
                ProductCategory.VULN_SCANNER: "需要多少个扫描引擎节点？",
                ProductCategory.DECEPTION: "需要部署多少个蜜罐？",
                ProductCategory.NDR: "需要分析多大流量（Mbps/Gbps）？",
                ProductCategory.API_SECURITY: "预计API流量多少QPS？",
                ProductCategory.CODE_SECURITY: "慧鉴静态代码安全测试，需要多少个并发扫描任务？",
                ProductCategory.CODE_DEVELOPMENT: "码力AI开发平台，需要多少个AI员工并发？",
                ProductCategory.ASSET: "云图互联网暴露面平台，请选择部署模式：一体化部署或管端分离部署？",
                ProductCategory.SOC: "万象安全运营平台，日均日志量EPS是多少？",
            }
            hint = hints.get(cat)
            if hint:
                return hint
            return "需要多大规格的配置？（如QPS、节点数、流量等）"

        # 仅对需要部署模式的产品询问
        needs_deployment = {
            ProductCategory.WAF: True,
            ProductCategory.HOST_SECURITY: True,
            ProductCategory.NDR: True,
            ProductCategory.API_SECURITY: True,
            ProductCategory.ASSET: True,
            ProductCategory.SOC: True,
        }
        if not requirements.deployment_mode and needs_deployment.get(requirements.product_category, False):
            return "需要什么部署模式？（单机/K8s集群/旁路等）"

        # localization 是可选的，不强制询问
        return None  # 需求已完整，返回None表示可以生成推荐

    def _build_question(
        self, requirements: UserRequirements, missing: List[str],
    ) -> str:
        """根据缺失字段生成追问"""
        if not requirements._has_product_spec():
            return (
                "请告诉我您需要哪种安全产品？可选类型：\n"
                "• 雷池 - Web应用防火墙\n"
                "• 牧云 - 主机安全\n"
                "• 洞鉴 - 漏洞扫描\n"
                "• 谛听 - 蜜罐诱捕\n"
                "• 全悉 - 流量分析(NDR)\n"
                "• API安全\n"
                "• 慧鉴 - 静态代码安全测试(SAST)\n"
                "• 码力 - AI智能开发平台\n"
                "• 云图 - 互联网暴露面资产管理\n"
                "• 万象 - 安全运营平台"
            )
        return "还需要了解以下信息：" + "、".join(missing) + "。请补充。"

    def _extract_quantity_from_notes(self, notes: str) -> int:
        """从备注中提取数量，格式: '数量: X个'"""
        if not notes:
            return 1
        import re
        match = re.search(r"数量:\s*(\d+)个", notes)
        if match:
            return int(match.group(1))
        return 1

    def _serialize_result(self, result: RecommendationResult) -> Dict[str, Any]:
        """序列化推荐结果，可选 LLM 润色推荐理由

        包含可选模块列表，用于前端模块选配
        """
        primary = result.primary_recommendation
        data = {
            "primary_recommendation": {
                "product": primary.product.name,
                "product_id": primary.product.product_id,
                "version": primary.version.name,
                "version_id": primary.version.version_id,
                "version_type": primary.version.version_type,
                "base_price": str(primary.version.get_base_price()),
                "selected_modules": [
                    {
                        "name": m.name,
                        "model": m.model,
                        "price": str(m.price),
                        "category": m.category.value,
                        "notes": m.notes,
                        "quantity": self._extract_quantity_from_notes(m.notes),
                    }
                    for m in primary.selected_modules
                ],
                "subtotal_price": str(primary.subtotal_price),
                "reasoning": primary.reasoning,
            },
            "alternatives": [
                {
                    "product": alt.product.name,
                    "version": alt.version.name,
                    "subtotal_price": str(alt.subtotal_price),
                    "reasoning": alt.reasoning,
                }
                for alt in result.alternatives
            ],
            "total_price": str(result.total_price),
            "discount_range": [str(result.discount_range[0]), str(result.discount_range[1])],
            "discount_min_price": str(
                result.total_price * result.discount_range[0]
            ),
            "discount_max_price": str(
                result.total_price * result.discount_range[1]
            ),
            "summary": result.summary,
            "additional_suggestions": result.additional_suggestions,
            # 新增：可选模块列表，用于前端选配
            "available_modules": get_optional_module_groups(primary.version),
        }

        # LLM 润色推荐理由
        llm_client = self._get_llm_client()
        if llm_client and llm_client.available:
            enhanced = _enhance_reasoning_with_llm(result, llm_client)
            if enhanced:
                data["primary_recommendation"]["reasoning"] = enhanced.get(
                    "reasoning", data["primary_recommendation"]["reasoning"]
                )
                data["summary"] = enhanced.get("summary", data["summary"])
                if enhanced.get("suggestions"):
                    data["additional_suggestions"] = enhanced["suggestions"]

        return data

    def format_result(self, result: Dict[str, Any]) -> str:
        """格式化结果为可读文本"""
        if result["type"] == "question":
            return result["question"]

        data = result["data"]
        primary = data["primary_recommendation"]
        lines = [
            "=" * 50,
            f"  推荐方案: {primary['product']} {primary['version']}",
            "=" * 50,
            "",
            f"  基础价格: ¥{primary['base_price']}",
        ]
        if primary["selected_modules"]:
            lines.append("")
            lines.append("  选配模块:")
            for m in primary["selected_modules"]:
                lines.append(f"    - {m['name']} ({m['model']}): ¥{m['price']}")
        lines.extend([
            "",
            f"  配置总价: ¥{data['total_price']}",
            f"  折扣范围: {data['discount_range'][0]} ~ {data['discount_range'][1]}",
            f"  折后价格: ¥{data['discount_min_price']} ~ ¥{data['discount_max_price']}",
            "",
            f"  {data['summary']}",
            "",
            f"  推荐理由: {primary['reasoning']}",
            "",
            "=" * 50,
        ])
        return "\n".join(lines)


def _merge_requirements(
    accumulated: UserRequirements, new: UserRequirements,
) -> UserRequirements:
    """合并两轮需求：新需求中的非空/非默认值覆盖累积需求

    特殊处理：
    - 产品类别：累积已有类别时，新的 LLM 瞎猜类别不覆盖（除非明确提及产品）
    - 数字字段：None/0 不覆盖已有值
    """
    acc_dict = accumulated.model_dump()
    new_dict = new.model_dump(exclude_none=True, exclude_unset=True)

    # 产品类别保护：累积已有类别，新输入若无明确产品关键词则不覆盖
    # 防止第二轮 "大概10000qps" 时 LLM 瞎猜类别覆盖正确的累积类别
    if acc_dict.get("product_category") is not None:
        # 检查新输入是否明确提及产品（关键词匹配）
        from product_selector.intent import extract_category
        explicit_cat = extract_category(new.notes or "")
        if explicit_cat is None and "product_category" in new_dict:
            # 新输入无明确产品关键词，但 LLM 返回了类别 -> 删除，保留累积的类别
            del new_dict["product_category"]

    # 对于布尔字段，只在 new 为 True 时才覆盖
    for key in ("localization_required", "ha_required"):
        if key in new_dict and not new_dict[key]:
            del new_dict[key]

    # 对于数字字段，None/0 不覆盖已有值
    for key in (
        "qps_requirement", "node_count", "mbps_requirement",
        "honeypot_count", "asset_count", "engine_count",
    ):
        if key in new_dict and (new_dict[key] is None or new_dict[key] == 0):
            del new_dict[key]

    acc_dict.update(new_dict)
    return UserRequirements(**acc_dict)


def _merge_llm_requirements(
    keyword_req: UserRequirements, llm_req: UserRequirements,
) -> UserRequirements:
    """合并 LLM 提取结果到关键词提取结果

    关键词结果优先。LLM 只补充缺失字段。
    """
    kw_dict = keyword_req.model_dump()

    for field in (
        "product_category", "product_name",
        "qps_requirement", "node_count", "mbps_requirement",
        "honeypot_count", "engine_count", "asset_count",
        "deployment_mode",
    ):
        if kw_dict.get(field) is None:
            llm_val = getattr(llm_req, field, None)
            if llm_val is not None:
                kw_dict[field] = llm_val

    # 布尔字段：关键词为 False 时 LLM 可补充
    if not kw_dict.get("localization_required") and llm_req.localization_required:
        kw_dict["localization_required"] = True
    if not kw_dict.get("ha_required") and llm_req.ha_required:
        kw_dict["ha_required"] = True

    # features_required: 合并去重
    kw_features = set(kw_dict.get("features_required", []) or [])
    llm_features = set(llm_req.features_required or [])
    kw_dict["features_required"] = list(kw_features | llm_features)

    # budget: 关键词优先
    if kw_dict.get("budget_max") is None and llm_req.budget_max is not None:
        kw_dict["budget_max"] = llm_req.budget_max

    return UserRequirements(**kw_dict)


def _enhance_reasoning_with_llm(
    result: RecommendationResult, llm_client: LLMClient,
) -> Optional[dict]:
    """用 LLM 润色推荐理由，生成更自然的销售话术"""
    primary = result.primary_recommendation
    modules_text = ""
    if primary.selected_modules:
        modules_text = "选配模块: " + ", ".join(
            f"{m.name}(¥{m.price})" for m in primary.selected_modules
        )

    prompt = f"""请将以下产品推荐理由润色为更自然的销售话术，保持专业但亲和。

产品: {primary.product.name}
版本: {primary.version.name}
配置总价: ¥{result.total_price}
折扣范围: {result.discount_range[0]} ~ {result.discount_range[1]}
原始推荐理由: {primary.reasoning}
{modules_text}
原始摘要: {result.summary}

返回格式:
{{
  "reasoning": "润色后的推荐理由(80-150字)",
  "summary": "一段话摘要(30-50字)",
  "suggestions": ["补充建议1", "补充建议2"]
}}"""

    response = llm_client.chat(
        [
            {"role": "system", "content": "你是一个安全产品售前专家，帮助润色产品推荐话术。只返回 JSON。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
    )
    if response is None:
        return None

    try:
        import json
        return json.loads(response)
    except (json.JSONDecodeError, TypeError):
        return None


def main():
    """命令行交互入口（多轮对话）"""
    import sys
    agent = ProductSelectorAgent(data_dir="data")
    session_id = "cli"
    print("安全产品智能选型助手 (输入 'quit' 退出, 'reset' 重新开始)")
    print("-" * 50)

    while True:
        try:
            user_input = input("\n请输入需求: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("再见!")
            break
        if user_input.lower() == "reset":
            agent.clear_session(session_id)
            print("已重置对话，请重新输入需求。")
            continue

        result = agent.process_with_session(user_input, session_id)
        print(agent.format_result(result))

        if result["type"] == "recommendation":
            agent.clear_session(session_id)


if __name__ == "__main__":
    main()