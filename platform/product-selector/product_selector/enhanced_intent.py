"""LLM 增强意图提取 - 从自然语言中结构化提取需求

当关键词匹配不够精确时，用 LLM 补充提取。
"""
import json
import re
from typing import Optional
from product_selector.models import UserRequirements, ProductCategory
from product_selector.llm_client import LLMClient


_INTENT_SYSTEM_PROMPT = """你是一个安全产品专家，帮助从用户描述中提取结构化需求。
请解析用户需求，返回 JSON 格式，只包含能确定的字段，不确定的设为 null。

产品类别 product_category 可选值:
- WAF: Web应用防火墙/雷池
- host_security: 主机安全/牧云/HIDS
- vuln_scanner: 漏洞扫描/洞鉴
- deception: 蜜罐诱捕/谛听
- ndr: 流量分析/全悉/NDR
- api_security: API安全
- code_security: 慧鉴/静态代码安全/SAST
- code_development: 码力/AI编程/AI开发平台
- asset: 云图/资产管理
- soc: 万象/安全运营/COSMOS

返回格式:
{
  "product_category": "WAF" | null,
  "product_name": "雷池" | null,
  "qps_requirement": 5000 | null,
  "node_count": 100 | null,
  "mbps_requirement": 500 | null,
  "honeypot_count": 20 | null,
  "engine_count": 3 | null,
  "asset_count": 500 | null,
  "concurrency_count": 5 | null,
  "eps_requirement": 10000 | null,
  "deployment_mode": "集群" | "K8s" | "单机" | "旁路" | null,
  "localization_required": true | false,
  "ha_required": true | false,
  "budget_max": 100000 | null,
  "features_required": ["Bot防护", "CC防护"] | [],
  "notes": "用户原始描述"
}

注意:
- 数字字段只返回数字，不要带单位
- budget_max 单位是元（万元要 * 10000）
- features_required 从用户提到的具体功能中提取
- 只有明确提到产品类型时才设置 product_category，否则设为 null
- 单纯提到 QPS/节点数/性能需求时，product_category 必须为 null
- 慧鉴(code_security)用于静态代码安全测试/SAST
- 码力(code_development)用于AI编程/AI开发平台
- 云图(asset)用于资产管理
- 万象(soc)用于安全运营平台"""


def extract_requirements_with_llm(
    user_input: str,
    llm_client: LLMClient,
) -> Optional[UserRequirements]:
    """用 LLM 从自然语言中提取结构化需求

    Args:
        user_input: 用户自然语言输入
        llm_client: LLM 客户端

    Returns:
        UserRequirements 或 None（LLM 不可用/解析失败时）
    """
    if not llm_client.available:
        return None

    response = llm_client.chat(
        [
            {"role": "system", "content": _INTENT_SYSTEM_PROMPT},
            {"role": "user", "content": user_input},
        ],
        temperature=0.0,
    )

    if response is None:
        return None

    return _parse_llm_response(response, user_input)


def _parse_llm_response(response: str, user_input: str = "") -> Optional[UserRequirements]:
    """解析 LLM 返回的 JSON"""
    try:
        data = json.loads(response)
    except json.JSONDecodeError:
        # 尝试提取 markdown code fence 中的 JSON
        m = re.search(r"```(?:json)?\s*([\s\S]*?)```", response)
        if m:
            try:
                data = json.loads(m.group(1))
            except json.JSONDecodeError:
                return None
        else:
            return None

    if not isinstance(data, dict):
        return None

    # 解析 category
    category = None
    cat_str = data.get("product_category")
    if isinstance(cat_str, str):
        try:
            category = ProductCategory(cat_str)
        except ValueError:
            pass

    # 解析 budget（可能是万元）
    budget = data.get("budget_max")
    if isinstance(budget, (int, float)) and budget > 0:
        from decimal import Decimal
        budget = Decimal(str(int(budget)))
    else:
        budget = None

    return UserRequirements(
        product_category=category,
        product_name=data.get("product_name"),
        qps_requirement=_int_or_none(data, "qps_requirement"),
        node_count=_int_or_none(data, "node_count"),
        mbps_requirement=_int_or_none(data, "mbps_requirement"),
        honeypot_count=_int_or_none(data, "honeypot_count"),
        engine_count=_int_or_none(data, "engine_count"),
        asset_count=_int_or_none(data, "asset_count"),
        deployment_mode=data.get("deployment_mode"),
        localization_required=bool(data.get("localization_required", False)),
        ha_required=bool(data.get("ha_required", False)),
        budget_max=budget,
        features_required=data.get("features_required", []) or [],
        notes=user_input,
    )


def _int_or_none(data: dict, key: str) -> Optional[int]:
    val = data.get(key)
    if isinstance(val, (int, float)) and val > 0:
        return int(val)
    return None
