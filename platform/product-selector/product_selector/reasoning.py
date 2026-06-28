"""推理选型模块 - 基于规则的版本筛选和模块推荐

支持全部 8 个产品类别的选型推荐:
  - WAF: QPS 容量匹配
  - HOST_SECURITY: 节点数匹配
  - DECEPTION: 蜜罐数匹配
  - NDR: Mbps 流量匹配
  - VULN_SCANNER: 引擎数匹配
  - API_SECURITY: 部署模式 + 容量
  - CODE_SECURITY: 功能模块匹配
  - ASSET: 部署规模匹配
"""
import re
import math
from decimal import Decimal
from typing import List, Optional, Dict, Any
from product_selector.models import (
    Product, Version, SoftwareVersion, HardwareVersion,
    Module, ModuleGroup, ModuleCategory,
    UserRequirements, ProductConfig, RecommendationResult,
    ProductCategory, VersionType,
)

DEFAULT_DISCOUNT_MIN = Decimal("0.85")
DEFAULT_DISCOUNT_MAX = Decimal("0.95")


def select_expansion_modules(
    version: Version, required_qps: int = 0, default_capacity: int = 1000,
) -> List[Module]:
    """为给定版本选择合适的扩容模块

    算法：贪心算法，尽可能精确匹配需求而不超额太多
    对于 3000QPS 需求 (基础1000)，需额外2000：
    - 有 1000QPS 和 10000QPS 模块，应选两个 1000QPS 模块
    """
    expansion_groups = [
        g for g in version.module_groups
        if not g.primary and not g.required
    ]
    expansion_modules: List[Module] = []

    needed = required_qps - default_capacity
    if needed <= 0:
        return []

    candidates: List[tuple[int, Module]] = []
    for group in expansion_groups:
        for m in group.modules:
            cap = _extract_capacity_from_name(m.name)
            if cap > 0:
                candidates.append((cap, m))

    if not candidates:
        return []

    candidates.sort(key=lambda x: x[0])

    remaining = needed

    while remaining > 0:
        added = False
        for i in range(len(candidates)-1, -1, -1):
            cap, mod = candidates[i]
            if cap <= remaining:
                expansion_modules.append(mod)
                remaining -= cap
                added = True
                break

        if not added:
            if candidates:
                smallest_cap, smallest_mod = candidates[0]
                expansion_modules.append(smallest_mod)
                remaining -= smallest_cap

    return expansion_modules


def _extract_capacity_from_name(name: str) -> int:
    """从模块名称提取容量数值"""
    # 匹配 "1000QPS", "10000QPS", "1万QPS" 等
    m = re.search(r"(\d+)\s*(?:QPS|万|个|节点|Mbps|蜜罐)", name)
    if m:
        val = int(m.group(1))
        if "万" in name:
            val *= 10000
        return val
    return 0


def select_value_added_modules(
    version: Version, requirements: UserRequirements,
) -> List[Module]:
    """根据需求推荐增值模块"""
    selected: List[Module] = []

    for group in version.module_groups:
        if group.primary or group.required:
            continue
        for m in group.modules:
            if m.category == ModuleCategory.LOCALIZATION:
                if requirements.localization_required:
                    selected.append(m)
            elif m.category == ModuleCategory.DEPLOYMENT:
                if requirements.deployment_mode:
                    if requirements.deployment_mode.lower() in m.name.lower():
                        selected.append(m)

    return selected


# ──────────────────────────────────────────────
#  WAF: 雷池 (Safeline)
# ──────────────────────────────────────────────

def recommend_for_waf(
    products: List[Product], requirements: UserRequirements,
) -> Optional[RecommendationResult]:
    """雷池 (WAF) 产品选型推荐

    国产化需求：选择HG硬件型号
    """
    waf_products = [p for p in products if p.category == ProductCategory.WAF]
    if not waf_products:
        return None

    product = waf_products[0]
    localization = requirements.localization_required
    qps_needed = requirements.qps_requirement or 0
    deployment = requirements.deployment_mode or ""

    # 国产化：选择HG硬件版本
    if localization and product.hardware_versions:
        # 选择匹配QPS的HG硬件版本
        if qps_needed <= 800:
            version_name = "SL-H20-HG-800"
        elif qps_needed <= 3000:
            version_name = "SL-H20-HG-3000"
        elif qps_needed <= 6000:
            version_name = "SL-H20-HG-6000"
        elif qps_needed <= 10000:
            version_name = "SL-H20-HG-10000"
        else:
            version_name = "SL-H20-HG-15000"

        version = product.get_hardware_version_by_name(version_name)
        if not version:
            # 尝试模糊匹配
            for hv in product.hardware_versions:
                if "HG" in hv.name:
                    version = hv
                    break

        if version:
            base_module = version.get_base_module()
            base_price = base_module.price if base_module else Decimal("0")
            return RecommendationResult(
                primary_recommendation=ProductConfig(
                    product=product,
                    version=version,
                    selected_modules=[],
                    subtotal_price=base_price,
                    reasoning=f"推荐{product.name}{version.name}国产化硬件版本，适配信创环境，支持{qps_needed}QPS防护需求",
                ),
                total_price=base_price,
                discount_range=(Decimal("1.0"), Decimal("1.0")),
                summary=f"推荐{product.name}国产化硬件版",
            )

    # 软件版本选型（非国产化）
    valid_versions = [
        v for v in product.software_versions
        if v.get_base_module() is not None and v.get_base_price() > 0
    ]

    if not valid_versions:
        return None

    # 根据部署模式和QPS选择版本
    selected_version = None
    if "集群" in deployment or qps_needed > 50000:
        selected_version = product.get_software_version_by_name("集群版")
    else:
        selected_version = product.get_software_version_by_name("单机版")

    # 如果按名称没找到，选择第一个有效版本
    if not selected_version:
        selected_version = sorted(valid_versions, key=lambda v: v.get_base_price())[0]

    base_module = selected_version.get_base_module()
    base_price = base_module.price if base_module else Decimal("0")

    expansion_modules = select_expansion_modules(selected_version, required_qps=qps_needed)
    expansion_price = sum(m.price for m in expansion_modules)

    value_added = select_value_added_modules(selected_version, requirements)
    va_price = sum(m.price for m in value_added)

    selected = expansion_modules + value_added
    subtotal = base_price + expansion_price + va_price

    reasoning = _build_waf_reasoning(
        selected_version, qps_needed, expansion_modules, value_added,
    )

    config = ProductConfig(
        product=product,
        version=selected_version,
        selected_modules=selected,
        subtotal_price=subtotal,
        reasoning=reasoning,
    )

    return RecommendationResult(
        primary_recommendation=config,
        total_price=subtotal,
        discount_range=(DEFAULT_DISCOUNT_MIN, DEFAULT_DISCOUNT_MAX),
        summary=_build_summary(product, selected_version, qps_needed, expansion_modules),
    )


def _build_waf_reasoning(
    version: Version, qps: int, expansions: List[Module], value_added: List[Module],
) -> str:
    parts = [f"选择{version.name}，基础防护QPS 1000，具备智能语义分析引擎"]
    if qps > 1000:
        parts.append(f"扩容至{qps}QPS（{' + '.join(m.name for m in expansions)}），确保高并发下的稳定防护")
    if value_added:
        parts.append(f"增值功能保障：{', '.join(m.name for m in value_added)}")
    parts.append("方案具备线性扩容能力，随业务增长灵活扩展")
    return "；".join(parts)


# ──────────────────────────────────────────────
#  HOST_SECURITY: 牧云 (Cloudwalker)
# ──────────────────────────────────────────────

# 版本名 -> (最小节点, 最大节点) 映射
_CLOUDWALKER_NODE_RANGES: Dict[str, tuple] = {
    "M100": (1, 100),
    "M500": (101, 500),
    "M1000": (501, 1000),
    "M3000": (1001, 3000),
    "MINF": (3001, float("inf")),
}


def recommend_for_host_security(
    products: List[Product], requirements: UserRequirements,
) -> Optional[RecommendationResult]:
    """牧云 (主机安全) 产品选型推荐 — 按节点数匹配版本

    牧云必须平台+探针一起选配：
    - 平台根据节点数选择版本 (M100/M500/M1000/M3000/MINF)
    - 探针数量等于节点数，按单价计费
    """
    candidates = [p for p in products if p.category == ProductCategory.HOST_SECURITY]
    if not candidates:
        return None

    product = candidates[0]
    node_count = requirements.node_count or 0

    # 排除 M-CNAPP / 单独配件，只匹配 M 系列
    m_versions = [
        v for v in product.software_versions
        if v.name in _CLOUDWALKER_NODE_RANGES
    ]
    if not m_versions:
        return None

    selected_version = _select_version_by_node_count(m_versions, node_count)
    base_module = selected_version.get_base_module()
    base_price = base_module.price if base_module else Decimal("0")

    # 选择探针模块（牧云必配）
    probe_modules, probe_qty, probe_price = _select_probe_modules_with_quantity(
        selected_version, node_count
    )

    # 增值功能
    feature_modules = _select_cloudwalker_features(selected_version, requirements)
    feature_price = sum(m.price for m in feature_modules)

    selected = probe_modules + feature_modules
    subtotal = base_price + probe_price + feature_price

    # 构建探针信息用于展示
    probe_info = ""
    if probe_modules and probe_qty > 0:
        probe_info = f"，含{probe_qty}个探针(¥{probe_price})"

    config = ProductConfig(
        product=product,
        version=selected_version,
        selected_modules=selected,
        subtotal_price=subtotal,
        reasoning=_build_host_security_reasoning(
            selected_version, node_count, probe_modules, probe_qty, feature_modules,
        ),
    )

    return RecommendationResult(
        primary_recommendation=config,
        total_price=subtotal,
        discount_range=(DEFAULT_DISCOUNT_MIN, DEFAULT_DISCOUNT_MAX),
        summary=f"推荐{product.name}{selected_version.name}，支持{node_count}节点{probe_info}",
    )


def _select_version_by_node_count(
    versions: List[SoftwareVersion], node_count: int,
) -> SoftwareVersion:
    """按节点数选择最小满足的版本"""
    if node_count <= 0:
        return versions[0]
    for v in versions:
        lo, hi = _CLOUDWALKER_NODE_RANGES.get(v.name, (0, 0))
        if node_count <= hi:
            return v
    return versions[-1]


def _select_probe_modules(
    version: SoftwareVersion, node_count: int,
) -> List[Module]:
    """为牧云版本选择探针模块

    探针数量等于节点数，每个探针有单价
    """
    if node_count <= 0:
        return []
    for group in version.module_groups:
        if "探针" in group.name:
            for m in group.modules:
                # 匹配对应版本的探针，如 探针-M100
                if version.name in m.name or f"探针-{version.name}" == m.name:
                    # 返回探针模块，价格会在计算时乘以数量
                    # 通过设置 notes 标记数量
                    m.notes = f"数量: {node_count}个"
                    return [m]
    return []


def _select_probe_modules_with_quantity(
    version: SoftwareVersion, node_count: int,
) -> tuple[List[Module], int, Decimal]:
    """为牧云版本选择探针模块，返回(模块列表, 数量, 总价)"""
    if node_count <= 0:
        return [], 0, Decimal("0")
    for group in version.module_groups:
        if "探针" in group.name:
            for m in group.modules:
                if version.name in m.name or f"探针-{version.name}" == m.name:
                    # 创建副本并设置数量备注
                    probe_module = Module(
                        name=m.name,
                        model=m.model,
                        description=m.description,
                        price=m.price,
                        unit=m.unit,
                        max_quantity=m.max_quantity,
                        discountable=m.discountable,
                        customizable=m.customizable,
                        category=m.category,
                        notes=f"数量: {node_count}个",
                    )
                    return [probe_module], node_count, m.price * node_count
    return [], 0, Decimal("0")


def _select_cloudwalker_features(
    version: SoftwareVersion, requirements: UserRequirements,
) -> List[Module]:
    """根据需求选择牧云附加功能"""
    selected: List[Module] = []
    for group in version.module_groups:
        if group.primary or group.name == "探针":
            continue
        for m in group.modules:
            if requirements.localization_required and "国产" in m.name:
                selected.append(m)
    return selected


def _build_host_security_reasoning(
    version: Version, node_count: int,
    probes: List[Module], probe_qty: int, features: List[Module],
) -> str:
    parts = [f"选择{version.name}，{node_count}节点规模，满足主机入侵检测与安全合规需求"]
    if probes and probe_qty > 0:
        probe_price = probes[0].price * probe_qty if probes else Decimal("0")
        parts.append(f"配套{probe_qty}个探针(¥{probe_price})，实现主机资产管理与入侵检测")
    if features:
        parts.append(f"扩展能力：{', '.join(m.name for m in features)}")
    parts.append("支持覆盖容器安全、云工作负载保护")
    return "；".join(parts)


# ──────────────────────────────────────────────
#  DECEPTION: 谛听 (Dsensor)
# ──────────────────────────────────────────────

_DSENSOR_HONEYPOT_LIMITS: Dict[str, int] = {
    "易捷版": 10,
    "标准版": 100,
    "高级版": 500,
    "尊享版": 2000,
}


def recommend_for_deception(
    products: List[Product], requirements: UserRequirements,
) -> Optional[RecommendationResult]:
    """谛听 (伪装欺骗) 产品选型推荐 — 按蜜罐数匹配"""
    candidates = [p for p in products if p.category == ProductCategory.DECEPTION]
    if not candidates:
        return None

    product = candidates[0]
    honeypot_count = requirements.honeypot_count or 10

    # 匹配版本: 选择满足蜜罐数的最小版本
    valid_versions = [
        v for v in product.software_versions
        if v.name in _DSENSOR_HONEYPOT_LIMITS
    ]
    selected_version = _select_dsensor_version(valid_versions, honeypot_count)
    base_module = selected_version.get_base_module()
    base_price = base_module.price if base_module else Decimal("0")

    config = ProductConfig(
        product=product,
        version=selected_version,
        selected_modules=[],
        subtotal_price=base_price,
        reasoning=f"选择{product.name}{selected_version.name}，"
                  f"最多支持{_DSENSOR_HONEYPOT_LIMITS.get(selected_version.name, 0)}个蜜罐，"
                  f"满足{honeypot_count}个蜜罐需求",
    )

    return RecommendationResult(
        primary_recommendation=config,
        total_price=base_price,
        discount_range=(DEFAULT_DISCOUNT_MIN, DEFAULT_DISCOUNT_MAX),
        summary=f"推荐{product.name}{selected_version.name}，"
                f"满足{honeypot_count}个蜜罐需求",
    )


def _select_dsensor_version(
    versions: List[SoftwareVersion], honeypot_count: int,
) -> SoftwareVersion:
    """选择满足蜜罐数的最小版本"""
    ordered = sorted(
        versions,
        key=lambda v: _DSENSOR_HONEYPOT_LIMITS.get(v.name, 0),
    )
    for v in ordered:
        limit = _DSENSOR_HONEYPOT_LIMITS.get(v.name, 0)
        if honeypot_count <= limit:
            return v
    return ordered[-1] if ordered else versions[0]


# ──────────────────────────────────────────────
#  NDR: 全悉 (Tanswer)
# ──────────────────────────────────────────────

# 软件版名称 -> 最大 Mbps
_TANSWER_MBPS_MAP: Dict[str, int] = {
    "TA-S10-500": 500,
    "TA-S10-1000": 1000,
    "TA-S10-2000": 2000,
    "TA-S10-5000": 5000,
    "TA-S10-10000": 10000,
}


def recommend_for_ndr(
    products: List[Product], requirements: UserRequirements,
) -> Optional[RecommendationResult]:
    """全悉 (NDR) 产品选型推荐

    国产化需求：选择HG硬件型号
    """
    candidates = [p for p in products if p.category == ProductCategory.NDR]
    if not candidates:
        return None

    product = candidates[0]
    mbps_needed = requirements.mbps_requirement or 500
    localization = requirements.localization_required

    # 国产化：选择HG硬件版本
    if localization and product.hardware_versions:
        # 选择匹配流量的HG硬件版本
        if mbps_needed <= 1000:
            version_name = "TA-H10-HG-1000（国产化型号-海光）"
        elif mbps_needed <= 5000:
            version_name = "TA-H10-HG-5000（国产化型号-海光）"
        else:
            version_name = "TA-H10-HG-10000（国产化型号-海光）"

        version = product.get_hardware_version_by_name(version_name)
        if not version:
            # 尝试模糊匹配
            for hv in product.hardware_versions:
                if "HG" in hv.name and str(mbps_needed) in hv.name:
                    version = hv
                    break

        if version:
            base_module = version.get_base_module()
            base_price = base_module.price if base_module else Decimal("0")
            return RecommendationResult(
                primary_recommendation=ProductConfig(
                    product=product,
                    version=version,
                    selected_modules=[],
                    subtotal_price=base_price,
                    reasoning=f"推荐{product.name}{version.name}国产化硬件版本，适配信创环境，支持{mbps_needed}Mbps流量分析",
                ),
                total_price=base_price,
                discount_range=(Decimal("1.0"), Decimal("1.0")),
                summary=f"推荐{product.name}国产化硬件版",
            )

    # 软件版本选型
    perf_versions = [
        v for v in product.software_versions
        if v.name in _TANSWER_MBPS_MAP
    ]
    selected_version = _select_tanswer_version(perf_versions, mbps_needed)
    base_module = selected_version.get_base_module()
    base_price = base_module.price if base_module else Decimal("0")

    config = ProductConfig(
        product=product,
        version=selected_version,
        selected_modules=[],
        subtotal_price=base_price,
        reasoning=f"选择{product.name}{selected_version.name}，"
                  f"最大实时分析流量{_TANSWER_MBPS_MAP.get(selected_version.name, 0)}Mbps，"
                  f"满足{mbps_needed}Mbps需求",
    )

    return RecommendationResult(
        primary_recommendation=config,
        total_price=base_price,
        discount_range=(DEFAULT_DISCOUNT_MIN, DEFAULT_DISCOUNT_MAX),
        summary=f"推荐{product.name}{selected_version.name}，满足{mbps_needed}Mbps流量分析需求",
    )


def _select_tanswer_version(
    versions: List[SoftwareVersion], mbps_needed: int,
) -> SoftwareVersion:
    """选择满足 Mbps 需求的最小版本"""
    ordered = sorted(
        versions,
        key=lambda v: _TANSWER_MBPS_MAP.get(v.name, 0),
    )
    for v in ordered:
        if mbps_needed <= _TANSWER_MBPS_MAP.get(v.name, 0):
            return v
    return ordered[-1] if ordered else versions[0]


# ──────────────────────────────────────────────
#  VULN_SCANNER: 洞鉴 (Xray)
# ──────────────────────────────────────────────

def recommend_for_vuln_scanner(
    products: List[Product], requirements: UserRequirements,
) -> Optional[RecommendationResult]:
    """洞鉴 (漏洞扫描) 产品选型推荐

    国产化需求：选择XC版(HG)软件版本
    """
    candidates = [p for p in products if p.category == ProductCategory.VULN_SCANNER]
    if not candidates:
        return None

    product = candidates[0]
    engine_count = requirements.engine_count or 1
    localization = requirements.localization_required

    # 国产化：选择XC版(HG)
    if localization:
        xc_version = product.get_software_version_by_name("XR-S10-HG（XC版）")
        if xc_version:
            base_module = xc_version.get_base_module()
            base_price = base_module.price if base_module else Decimal("0")

            # 添加国产化授权模块
            localization_modules = []
            for group in xc_version.module_groups:
                if "国产化" in group.name:
                    localization_modules.extend(group.modules)

            subtotal = base_price + sum(m.price for m in localization_modules)

            return RecommendationResult(
                primary_recommendation=ProductConfig(
                    product=product,
                    version=xc_version,
                    selected_modules=localization_modules,
                    subtotal_price=subtotal,
                    reasoning=f"推荐{product.name}XC版（国产化），适配信创环境",
                ),
                total_price=subtotal,
                discount_range=(DEFAULT_DISCOUNT_MIN, DEFAULT_DISCOUNT_MAX),
                summary=f"推荐{product.name}国产化版本",
            )

    # 非国产化：标准版
    std_version = product.get_software_version_by_name("XR-S10-T10")
    if not std_version:
        sw_versions = [v for v in product.software_versions if v.name not in ("单独模块",)]
        if not sw_versions:
            return None
        std_version = sw_versions[0]

    base_module = std_version.get_base_module()
    base_price = base_module.price if base_module else Decimal("0")

    # 如需额外引擎，从引擎版获取引擎扩容模块
    extra_engines: List[Module] = []
    if engine_count > 1:
        extra_needed = engine_count - 1
        en_version = product.get_software_version_by_name("XR-S10-EN（引擎）")
        if en_version:
            for group in en_version.module_groups:
                for m in group.modules:
                    if "引擎" in m.name or "引擎节点" in m.name:
                        for _ in range(extra_needed):
                            extra_engines.append(m)
                        break

    expansion_price = sum(m.price for m in extra_engines)
    subtotal = base_price + expansion_price

    config = ProductConfig(
        product=product,
        version=std_version,
        selected_modules=extra_engines,
        subtotal_price=subtotal,
        reasoning=f"选择{product.name}标准版（含管理节点*1+引擎节点*1），"
                  + (f"扩容{engine_count - 1}个引擎节点" if engine_count > 1
                     else "满足基础扫描需求"),
    )

    return RecommendationResult(
        primary_recommendation=config,
        total_price=subtotal,
        discount_range=(DEFAULT_DISCOUNT_MIN, DEFAULT_DISCOUNT_MAX),
        summary=f"推荐{product.name}标准版，{engine_count}个引擎节点",
    )


# ──────────────────────────────────────────────
#  API_SECURITY: API
# ──────────────────────────────────────────────

_API_VERSION_ORDER = ["标准单机版", "增强单机版", "标准集群版", "高级集群版"]


def recommend_for_api_security(
    products: List[Product], requirements: UserRequirements,
) -> Optional[RecommendationResult]:
    """API 安全产品选型推荐

    国产化需求：选择HG硬件型号
    """
    candidates = [p for p in products if p.category == ProductCategory.API_SECURITY]
    if not candidates:
        return None

    product = candidates[0]
    localization = requirements.localization_required
    qps = requirements.qps_requirement or 0
    deployment = requirements.deployment_mode or ""

    # 国产化：选择HG硬件版本
    if localization and product.hardware_versions:
        # 选择匹配QPS的HG硬件版本
        if qps <= 3000:
            version_name = "API-H30-HG-3000"
        elif qps <= 6000:
            version_name = "API-H30-HG-6000"
        else:
            version_name = "API-H30-HG-15000"

        version = product.get_hardware_version_by_name(version_name)
        if not version:
            # 尝试模糊匹配
            for hv in product.hardware_versions:
                if "HG" in hv.name:
                    version = hv
                    break

        if version:
            base_module = version.get_base_module()
            base_price = base_module.price if base_module else Decimal("0")
            return RecommendationResult(
                primary_recommendation=ProductConfig(
                    product=product,
                    version=version,
                    selected_modules=[],
                    subtotal_price=base_price,
                    reasoning=f"推荐{product.name}{version.name}国产化硬件版本，适配信创环境",
                ),
                total_price=base_price,
                discount_range=(Decimal("1.0"), Decimal("1.0")),
                summary=f"推荐{product.name}国产化硬件版",
            )

    # 软件版本选型
    selected_version: Optional[SoftwareVersion] = None
    if "集群" in deployment:
        selected_version = product.get_software_version_by_name("标准集群版")
    elif qps > 5000:
        selected_version = product.get_software_version_by_name("高级集群版")
    else:
        selected_version = product.get_software_version_by_name("标准单机版")

    if not selected_version:
        if product.software_versions:
            selected_version = product.software_versions[0]
        else:
            return None

    base_module = selected_version.get_base_module()
    base_price = base_module.price if base_module else Decimal("0")

    # 增值模块
    value_modules: List[Module] = []
    for group in selected_version.module_groups:
        if group.primary:
            continue
        for m in group.modules:
            if requirements.features_required and any(
                f in m.name for f in requirements.features_required
            ):
                value_modules.append(m)

    value_price = sum(m.price for m in value_modules)
    subtotal = base_price + value_price

    config = ProductConfig(
        product=product,
        version=selected_version,
        selected_modules=value_modules,
        subtotal_price=subtotal,
        reasoning=(
            f"选择{product.name}{selected_version.name}"
            + (f"，适合{'集群化大规模' if '集群' in deployment else '单机一体化'}部署"
               if deployment else "，一体化集成采集/分析/管理节点")
            + ("，支持API资产梳理、安全检测、脆弱性发现和异常行为分析"
               if "集群" in selected_version.name else "")
            + (f"，满足{'高并发' if qps > 5000 else '企业级'}API安全防护需求"
               if qps > 0 else "")
        ),
    )

    return RecommendationResult(
        primary_recommendation=config,
        total_price=subtotal,
        discount_range=(DEFAULT_DISCOUNT_MIN, DEFAULT_DISCOUNT_MAX),
        summary=f"推荐{product.name}{selected_version.name}",
    )


# ──────────────────────────────────────────────
#  CODE_SECURITY: 慧鉴/码力 (Codeinsight/Codeforce)
# ──────────────────────────────────────────────

def recommend_for_code_security(
    products: List[Product], requirements: UserRequirements,
) -> Optional[RecommendationResult]:
    """代码安全产品选型推荐 — 慧鉴(SAST) / 码力(AI编程)"""
    code_products = [p for p in products if p.category == ProductCategory.CODE_SECURITY]
    if not code_products:
        return None

    # 如果指定了产品名，优先匹配；否则返回两个产品的基础方案
    if requirements.product_name:
        matched = [p for p in code_products if requirements.product_name in p.name]
        product = matched[0] if matched else code_products[0]
    else:
        product = code_products[0]

    if not product.software_versions:
        return None

    version = product.software_versions[0]
    base_module = version.get_base_module()
    base_price = base_module.price if base_module else Decimal("0")

    # 选配扩展模块
    extra_modules: List[Module] = []
    for group in version.module_groups:
        if group.primary:
            continue
        for m in group.modules:
            if requirements.features_required:
                for f in requirements.features_required:
                    if f in m.name:
                        extra_modules.append(m)
                        break

    extra_price = sum(m.price for m in extra_modules)
    subtotal = base_price + extra_price

    config = ProductConfig(
        product=product,
        version=version,
        selected_modules=extra_modules,
        subtotal_price=subtotal,
        reasoning=(
            f"选择{product.name}{version.name}"
            + (f"，涵盖SAST静态代码分析、SCA组件分析等核心能力"
               if "慧鉴" in product.name else
               "，AI驱动的代码安全研发助手，提升开发效率")
            + (f"，附加模块：{', '.join(m.name for m in extra_modules)}"
               if extra_modules else "的基础方案，性价比最优")
        ),
    )

    return RecommendationResult(
        primary_recommendation=config,
        total_price=subtotal,
        discount_range=(DEFAULT_DISCOUNT_MIN, DEFAULT_DISCOUNT_MAX),
        summary=f"推荐{product.name}{version.name}",
    )


# ──────────────────────────────────────────────
#  ASSET: 云图 (Cloudatlas) - 互联网暴露面资产管理平台
# ──────────────────────────────────────────────

def recommend_for_cloudatlas(
    products: List[Product], requirements: UserRequirements,
) -> Optional[RecommendationResult]:
    """云图(Cloudatlas)选型推荐 - 互联网暴露面资产管理平台

    选型依据：
    1. 国产化需求：HG型号为国产化版本
    2. 部署模式：一体化部署、管端分离部署
    """
    asset_products = [p for p in products if p.category == ProductCategory.ASSET]
    if not asset_products:
        return None

    product = asset_products[0]

    # 云图软件版无定价，推荐硬件版
    if not product.hardware_versions:
        return None

    localization = requirements.localization_required
    deployment = requirements.deployment_mode or ""

    # 根据部署模式和国产化需求选择版本
    # 管/端分离部署：分布式场景
    # 一体化部署：根据国产化需求选择HG或非HG型号
    if "管端分离" in deployment or "分离" in deployment:
        version_name = "管/端分离部署模式"
    elif localization:
        # 国产化需求：选择HG型号
        version_name = "CA-H10-HG-P128（一体化部署模式）"
    else:
        # 非国产化：选择P64型号
        version_name = "CA-H10-P64（一体化部署模式）"

    version = (
        product.get_hardware_version_by_name(version_name)
        or product.hardware_versions[0]
    )

    # 获取基础设备价格
    base_module = version.get_base_module()
    base_price = base_module.price if base_module else Decimal("0")

    config = ProductConfig(
        product=product,
        version=version,
        selected_modules=[],
        subtotal_price=base_price,
        reasoning=(
            f"推荐{product.name}{version.name}"
            + ("，国产化版本适配信创环境" if "HG" in version_name else "")
            + ("，管端分离架构适合分布式部署场景" if "分离" in version_name else
               "，一体化部署简洁高效")
            + "，提供互联网资产发现、暴露面监测能力"
        ),
    )

    return RecommendationResult(
        primary_recommendation=config,
        total_price=base_price,
        discount_range=(Decimal("1.0"), Decimal("1.0")),  # 硬件通常不打折
        summary=f"推荐{product.name}{version.name}互联网暴露面资产管理平台",
    )


# ──────────────────────────────────────────────
#  SOC: 万象 (Cosmos) - 安全分析与运营平台
# ──────────────────────────────────────────────

def recommend_for_cosmos(
    products: List[Product], requirements: UserRequirements,
) -> Optional[RecommendationResult]:
    """万象(Cosmos)选型推荐 - 安全分析与运营平台

    国产化需求：选择HG硬件型号
    """
    soc_products = [p for p in products if p.category == ProductCategory.SOC]
    if not soc_products:
        return None

    product = soc_products[0]
    localization = requirements.localization_required
    eps = requirements.eps_requirement or 0
    deployment = requirements.deployment_mode or ""

    # 国产化：选择HG硬件版本
    if localization and product.hardware_versions:
        # 选择匹配EPS的HG硬件版本
        if eps <= 1000:
            version_name = "CM-H10-HG-1000（国产化Tiny版）"
        elif eps <= 5000:
            version_name = "CM-H10-HG-5000（国产化版）"
        else:
            version_name = "CM-H10-HG-10000（国产化版）"

        version = product.get_hardware_version_by_name(version_name)
        if not version:
            # 尝试模糊匹配
            for hv in product.hardware_versions:
                if "HG" in hv.name:
                    version = hv
                    break

        if version:
            base_module = version.get_base_module()
            base_price = base_module.price if base_module else Decimal("0")
            return RecommendationResult(
                primary_recommendation=ProductConfig(
                    product=product,
                    version=version,
                    selected_modules=[],
                    subtotal_price=base_price,
                    reasoning=f"推荐{product.name}{version.name}国产化硬件版本，适配信创环境",
                ),
                total_price=base_price,
                discount_range=(Decimal("1.0"), Decimal("1.0")),
                summary=f"推荐{product.name}国产化硬件版",
            )

    # 软件版本选型
    if not product.software_versions:
        return None

    asset_count = requirements.asset_count or 0

    # 按日志量(EPS)和资产规模选择版本
    if deployment == "集群部署" or eps > 10000:
        version_name = "集群（企业版）"
    elif eps > 5000 or asset_count > 5000:
        version_name = "单机（企业版）"
    else:
        version_name = "单机（Mini版）"

    version = (
        product.get_software_version_by_name(version_name)
        or product.get_software_version_by_name("单机（企业版）")
        or product.software_versions[0]
    )
    base_module = version.get_base_module()
    base_price = base_module.price if base_module else Decimal("0")

    config = ProductConfig(
        product=product,
        version=version,
        selected_modules=[],
        subtotal_price=base_price,
        reasoning=(
            f"选择{product.name}{version.name}"
            + (f"，适合日均{eps}EPS日志量规模" if eps > 0 else "")
            + (f"，管理约{asset_count}资产" if asset_count > 0 else "")
            + ("，集群架构支持弹性扩容和高可用" if "集群" in version_name else
               "，单机部署简洁高效")
        ),
    )

    return RecommendationResult(
        primary_recommendation=config,
        total_price=base_price,
        discount_range=(DEFAULT_DISCOUNT_MIN, DEFAULT_DISCOUNT_MAX),
        summary=f"推荐{product.name}{version.name}安全运营平台",
    )


# ──────────────────────────────────────────────
#  CODE_DEVELOPMENT: 码力 (Codeforce) - AI智能开发平台
# ──────────────────────────────────────────────

def recommend_for_code_development(
    products: List[Product], requirements: UserRequirements,
) -> Optional[RecommendationResult]:
    """码力(Codeforce)选型推荐 - AI智能开发平台"""
    dev_products = [p for p in products if p.category == ProductCategory.CODE_DEVELOPMENT]
    if not dev_products:
        return None

    product = dev_products[0]

    if not product.software_versions:
        return None

    concurrency = requirements.concurrency_count or 5

    # 码力私有化软件标准版
    version = product.software_versions[0]
    base_module = version.get_base_module()
    base_price = base_module.price if base_module else Decimal("0")

    # 根据并发数计算扩展模块需求
    # 基础版支持5个AI员工并发，需要扩展时选配并发授权模块
    selected_modules = []
    extra_concurrency = concurrency - 5 if concurrency > 5 else 0

    if extra_concurrency > 0:
        for group in version.module_groups:
            if "授权" in group.name:
                for m in group.modules:
                    if "AI员工并发" in m.name:
                        # 根据描述或型号匹配
                        desc = m.description or ""
                        if f"扩展{extra_concurrency}个" in desc:
                            selected_modules.append(m)
                            break
                        elif m.model == "CF-S10-STD-SPLV-EA101" and extra_concurrency <= 5:
                            selected_modules.append(m)
                            break
                        elif m.model == "CF-S10-STD-SPLV-EA102" and extra_concurrency <= 10:
                            selected_modules.append(m)
                            break
                        elif m.model == "CF-S10-STD-SPLV-EA103" and extra_concurrency <= 20:
                            selected_modules.append(m)
                            break

    module_price = sum(m.price for m in selected_modules)
    subtotal = base_price + module_price

    reasoning = (
        f"推荐{product.name}{version.name}"
        + f"，支持{concurrency}个AI员工并发"
    )
    if selected_modules:
        reasoning += f"（基础5个+扩展{extra_concurrency}个）"
    reasoning += "，提供AI编程辅助、代码智能生成能力"

    config = ProductConfig(
        product=product,
        version=version,
        selected_modules=selected_modules,
        subtotal_price=subtotal,
        reasoning=reasoning,
    )

    return RecommendationResult(
        primary_recommendation=config,
        total_price=subtotal,
        discount_range=(DEFAULT_DISCOUNT_MIN, DEFAULT_DISCOUNT_MAX),
        summary=f"推荐{product.name}AI智能开发平台",
    )


# ──────────────────────────────────────────────
#  通用构建辅助
# ──────────────────────────────────────────────

def _build_detailed_reasoning(
    product_name: str,
    version_name: str,
    requirement_desc: str,
    advantage_points: list,
    alternatives_considered: list = None,
) -> str:
    """构建详细的销售友好推荐理由

    Args:
        product_name: 产品名称
        version_name: 推荐版本名
        requirement_desc: 需求描述（如"5000QPS流量防护"）
        advantage_points: 优势点列表
        alternatives_considered: 考虑过的备选版本及其不选原因
    """
    parts = [f"推荐{product_name}{version_name}，{requirement_desc}"]
    if advantage_points:
        parts.append("优势：" + "；".join(advantage_points))
    if alternatives_considered:
        parts.append("对比：" + "；".join(alternatives_considered))
    return "。".join(parts)


def _build_summary(
    product: Product, version: Version, qps: int, expansions: List[Module],
) -> str:
    parts = [f"推荐{product.name}{version.name}"]
    if qps > 0:
        parts.append(f"满足{qps}QPS需求")
    if expansions:
        parts.append(f"含{len(expansions)}个扩容模块")
    return "，".join(parts)


def _match_products(
    products: List[Product], requirements: UserRequirements,
) -> List[Product]:
    """根据需求匹配产品"""
    matched: List[Product] = []

    for p in products:
        if requirements.product_name and requirements.product_name in p.name:
            matched.append(p)
        elif requirements.product_category and p.category == requirements.product_category:
            matched.append(p)

    if not matched:
        return products

    return matched


def get_optional_module_groups(version: Version) -> List[Dict[str, Any]]:
    """获取版本的可选模块组（非主组且非必选）

    用于前端展示模块选配列表
    """
    optional_groups = []
    for group in version.module_groups:
        if group.primary or group.required:
            continue
        group_data = {
            "name": group.name,
            "multi_select": group.multi_select,
            "max_quantity": group.max_quantity,
            "modules": []
        }
        for m in group.modules:
            group_data["modules"].append({
                "name": m.name,
                "model": m.model,
                "description": m.description,
                "price": str(m.price),
                "unit": m.unit,
                "max_quantity": m.max_quantity,
                "discountable": m.discountable,
                "category": m.category.value,
            })
        if group_data["modules"]:
            optional_groups.append(group_data)
    return optional_groups


def filter_valid_versions(
    versions: List[Version], version_type: str = None
) -> List[Version]:
    """筛选有效独立版本

    排除 "单独模块" 等非独立版本，只保留有基础模块且价格>0的版本
    """
    valid = []
    for v in versions:
        # 检查是否有有效的基础模块
        base = v.get_base_module()
        if base is None:
            continue
        if v.get_base_price() <= 0:
            continue
        # 排除名称为"单独模块"或"单独配件"的版本
        if "单独" in v.name:
            continue
        # 版本类型过滤
        if version_type and v.version_type != version_type:
            continue
        valid.append(v)
    return valid


# 产品类型到推荐函数的映射
_RECOMMEND_HANDLERS: dict[ProductCategory, callable] = {
    ProductCategory.WAF: recommend_for_waf,
    ProductCategory.HOST_SECURITY: recommend_for_host_security,
    ProductCategory.DECEPTION: recommend_for_deception,
    ProductCategory.NDR: recommend_for_ndr,
    ProductCategory.VULN_SCANNER: recommend_for_vuln_scanner,
    ProductCategory.API_SECURITY: recommend_for_api_security,
    ProductCategory.CODE_SECURITY: recommend_for_code_security,
    ProductCategory.CODE_DEVELOPMENT: recommend_for_code_development,
    ProductCategory.ASSET: recommend_for_cloudatlas,
    ProductCategory.SOC: recommend_for_cosmos,
}


def recommend(
    products: List[Product], requirements: UserRequirements,
) -> Optional[RecommendationResult]:
    """根据需求生成推荐结果"""
    if not requirements.is_complete():
        return None

    matched = _match_products(products, requirements)

    if requirements.product_category:
        handler = _RECOMMEND_HANDLERS.get(requirements.product_category)
        if handler:
            return handler(matched, requirements)

    if matched:
        return _default_recommend(matched, requirements)

    return None


def _default_recommend(
    products: List[Product], requirements: UserRequirements,
) -> Optional[RecommendationResult]:
    """默认推荐逻辑（兜底）"""
    if not products:
        return None
    product = products[0]
    all_versions = product.get_all_versions()
    if not all_versions:
        return None
    sw_sorted = sorted(
        [v for v in all_versions if isinstance(v, SoftwareVersion)],
        key=lambda v: v.get_base_price(),
    )
    version = sw_sorted[0] if sw_sorted else all_versions[0]
    base = version.get_base_module()
    base_price = base.price if base else Decimal("0")

    config = ProductConfig(
        product=product,
        version=version,
        selected_modules=[],
        subtotal_price=base_price,
        reasoning=f"推荐{product.name}{version.name}作为基础方案",
    )
    return RecommendationResult(
        primary_recommendation=config,
        total_price=base_price,
        discount_range=(DEFAULT_DISCOUNT_MIN, DEFAULT_DISCOUNT_MAX),
        summary=f"推荐{product.name}{version.name}",
    )
