"""意图理解模块 - 从自然语言输入提取结构化需求

MVP 阶段使用关键词匹配，不依赖 LLM。
支持提取：产品类型、产品名称、性能需求、部署模式、国产化需求、预算。
"""
import re
from decimal import Decimal
from typing import Optional
from product_selector.models import UserRequirements, ProductCategory

# 产品名关键词 -> ProductCategory
CATEGORY_KEYWORDS: dict[str, ProductCategory] = {
    "WAF": ProductCategory.WAF,
    "waf": ProductCategory.WAF,
    "雷池": ProductCategory.WAF,
    "Web应用防火墙": ProductCategory.WAF,
    "主机安全": ProductCategory.HOST_SECURITY,
    "牧云": ProductCategory.HOST_SECURITY,
    "HIDS": ProductCategory.HOST_SECURITY,
    "漏洞扫描": ProductCategory.VULN_SCANNER,
    "洞鉴": ProductCategory.VULN_SCANNER,
    "蜜罐": ProductCategory.DECEPTION,
    "谛听": ProductCategory.DECEPTION,
    "诱捕": ProductCategory.DECEPTION,
    "流量分析": ProductCategory.NDR,
    "全悉": ProductCategory.NDR,
    "NDR": ProductCategory.NDR,
    "API安全": ProductCategory.API_SECURITY,
    "慧鉴": ProductCategory.CODE_SECURITY,
    "SAST": ProductCategory.CODE_SECURITY,
    "静态代码": ProductCategory.CODE_SECURITY,
    "代码安全测试": ProductCategory.CODE_SECURITY,
    "码力": ProductCategory.CODE_DEVELOPMENT,
    "AI编程": ProductCategory.CODE_DEVELOPMENT,
    "AI开发": ProductCategory.CODE_DEVELOPMENT,
    "智能开发": ProductCategory.CODE_DEVELOPMENT,
    "资产管理": ProductCategory.ASSET,
    "云图": ProductCategory.ASSET,
    "万象": ProductCategory.SOC,
    "SOC": ProductCategory.SOC,
    "安全运营": ProductCategory.SOC,
    "COSMOS": ProductCategory.SOC,
}

# 产品名关键词
PRODUCT_KEYWORDS: dict[str, str] = {
    "雷池": "雷池",
    "牧云": "牧云",
    "洞鉴": "洞鉴",
    "谛听": "谛听",
    "全悉": "全悉",
    "慧鉴": "慧鉴",
    "码力": "码力",
    "云图": "云图",
    "万象": "万象",
}

DEPLOYMENT_KEYWORDS: dict[str, str] = {
    "K8s": "K8s",
    "k8s": "K8s",
    "kubernetes": "K8s",
    "集群": "集群",
    "单机": "单机",
    "SDK": "SDK",
    "sdk": "SDK",
    "反向代理": "反向代理",
    "旁路": "旁路",
    "镜像": "镜像流量",
    "串联": "串联",
}

LOCALIZATION_KEYWORDS = [
    "国产化", "国产", "信创", "麒麟", "统信", "中标麒麟",
    "银河麒麟", "达梦", "人大金仓", "kingbase",
]

BUDGET_PATTERNS = [
    (re.compile(r"预算[在]?(\d+(?:\.\d+)?)\s*万"), 10000),
    (re.compile(r"预算[在]?(\d+(?:\.\d+)?)\s*[万w]"), 10000),
    (re.compile(r"(\d+(?:\.\d+)?)\s*万[以之内]?[内下]?"), 10000),
    (re.compile(r"预算[在]?(\d+)"), 1),
]


def extract_qps(text: str) -> Optional[int]:
    """从文本中提取 QPS 需求"""
    # 匹配 "5000 QPS" 或 "5000QPS"
    m = re.search(r"(\d+)\s*QPS", text, re.IGNORECASE)
    if m:
        return int(m.group(1))
    # 匹配 "1万QPS" 或 "1w QPS"
    m = re.search(r"(\d+(?:\.\d+)?)\s*[万w]\s*QPS", text, re.IGNORECASE)
    if m:
        return int(float(m.group(1)) * 10000)
    # 匹配 "每秒5000次"
    m = re.search(r"每秒\s*(\d+)\s*次", text)
    if m:
        return int(m.group(1))
    return None


def extract_node_count(text: str) -> Optional[int]:
    """提取节点/服务器数量"""
    m = re.search(r"(\d+)\s*(?:台|个)?\s*(?:服务器|节点|主机|终端|资产)", text)
    if m:
        return int(m.group(1))
    return None


def extract_mbps(text: str) -> Optional[int]:
    """提取流量 Mbps 需求"""
    m = re.search(r"(\d+)\s*Mbps", text, re.IGNORECASE)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d+)\s*[Gg]bps", text)
    if m:
        return int(m.group(1)) * 1000
    return None


def extract_honeypot_count(text: str) -> Optional[int]:
    """提取蜜罐数量"""
    m = re.search(r"(\d+)\s*(?:个)?\s*蜜罐", text)
    if m:
        return int(m.group(1))
    return None


def extract_engine_count(text: str) -> Optional[int]:
    """提取引擎数量"""
    m = re.search(r"(\d+)\s*(?:个)?\s*(?:扫描)?引擎", text)
    if m:
        return int(m.group(1))
    return None


def extract_asset_count(text: str) -> Optional[int]:
    """提取资产数量"""
    m = re.search(r"(\d+)\s*(?:个|台)?\s*(?:资产|日志)", text)
    if m:
        return int(m.group(1))
    return None


def extract_product_name(text: str) -> Optional[str]:
    """从文本中提取产品名称"""
    for keyword, name in PRODUCT_KEYWORDS.items():
        if keyword in text:
            return name
    return None


def extract_category(text: str) -> Optional[ProductCategory]:
    """从文本中推断产品类别"""
    # 优先级匹配：更长的关键词优先
    sorted_keywords = sorted(CATEGORY_KEYWORDS.keys(), key=len, reverse=True)
    for keyword in sorted_keywords:
        if keyword in text:
            return CATEGORY_KEYWORDS[keyword]
    return None


def detect_deployment_mode(text: str) -> Optional[str]:
    """检测部署模式"""
    for keyword, mode in DEPLOYMENT_KEYWORDS.items():
        if keyword in text:
            return mode
    return None


def detect_localization(text: str) -> bool:
    """检测是否需要国产化"""
    return any(kw in text for kw in LOCALIZATION_KEYWORDS)


def extract_budget(text: str) -> Optional[Decimal]:
    """提取预算上限"""
    for pattern, multiplier in BUDGET_PATTERNS:
        m = pattern.search(text)
        if m:
            value = float(m.group(1)) * multiplier
            return Decimal(str(int(value)))
    return None


def extract_requirements(user_input: str) -> UserRequirements:
    """从用户输入提取结构化需求

    Args:
        user_input: 用户自然语言输入

    Returns:
        UserRequirements 对象
    """
    return UserRequirements(
        product_category=extract_category(user_input),
        product_name=extract_product_name(user_input),
        qps_requirement=extract_qps(user_input),
        node_count=extract_node_count(user_input),
        mbps_requirement=extract_mbps(user_input),
        honeypot_count=extract_honeypot_count(user_input),
        engine_count=extract_engine_count(user_input),
        asset_count=extract_asset_count(user_input),
        deployment_mode=detect_deployment_mode(user_input),
        localization_required=detect_localization(user_input),
        budget_max=extract_budget(user_input),
        notes=user_input,
    )


def extract_requirements_form(data: dict) -> UserRequirements:
    """从结构化表单数据创建 UserRequirements

    Args:
        data: 表单数据字典，支持的键：
            - product_category: str (如 "WAF")
            - qps_requirement: int
            - node_count: int
            - mbps_requirement: int
            - honeypot_count: int
            - engine_count: int
            - asset_count: int
            - deployment_mode: str
            - localization_required: bool
            - ha_required: bool
            - budget_max: int (万元) 或 Decimal

    Returns:
        UserRequirements 对象
    """
    category = data.get("product_category")
    if isinstance(category, str):
        try:
            category = ProductCategory(category)
        except ValueError:
            category = None

    budget = data.get("budget_max")
    if isinstance(budget, (int, float)) and budget > 0:
        budget = Decimal(str(int(budget * 10000)))  # 万元转元
    elif isinstance(budget, Decimal):
        pass
    else:
        budget = None

    return UserRequirements(
        product_category=category,
        product_name=data.get("product_name"),
        qps_requirement=data.get("qps_requirement"),
        node_count=data.get("node_count"),
        mbps_requirement=data.get("mbps_requirement"),
        honeypot_count=data.get("honeypot_count"),
        engine_count=data.get("engine_count"),
        asset_count=data.get("asset_count"),
        deployment_mode=data.get("deployment_mode"),
        localization_required=bool(data.get("localization_required", False)),
        ha_required=bool(data.get("ha_required", False)),
        budget_max=budget,
        notes=data.get("notes"),
    )