"""Markdown 产品数据解析器

解析 data/*.md 文件中的产品清单，转换为 Pydantic 数据模型。
数据格式约定:
  - 以 `# 产品名 产品清单` 开头提取产品名
  - `**产品ID**: <id>` 提取产品ID
  - `## 软件版` / `## 硬件版` 分区
  - `### 版本对比` 下的表格为版本列表
  - `### 软件版 N: 版本名` 为版本详情，下面每个 `#### 模块组名` 为模块组
  - 每个模块组包含属性表格和模块表格
"""
import re
import os
from decimal import Decimal
from typing import List, Dict, Any, Tuple
from product_selector.models import (
    Product, ProductCategory, SoftwareVersion, HardwareVersion,
    Module, ModuleGroup, ModuleCategory,
)


def parse_price(price_str: str) -> Decimal:
    """解析价格字符串为 Decimal"""
    if not price_str or not price_str.strip():
        return Decimal("0")
    cleaned = price_str.strip().replace("¥", "").replace(",", "").replace("￥", "")
    try:
        return Decimal(cleaned)
    except Exception:
        return Decimal("0")


def _extract_version_id(line: str) -> str:
    m = re.search(r"\*\*版本ID\*\*[：:]\s*`?([a-f0-9]+)`?", line)
    return m.group(1) if m else ""


def _extract_version_number(line: str) -> int:
    m = re.search(r"版本号[：:]\s*(\d+)", line)
    return int(m.group(1)) if m else 0


def _parse_property_table(lines: List[str]) -> Dict[str, Any]:
    """解析属性表格，返回属性字典"""
    props: Dict[str, Any] = {
        "required": False,
        "multi_select": False,
        "primary": False,
        "maintenance_group": False,
        "max_quantity": 0,
    }
    for line in lines:
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) < 2:
            continue
        key, val = cells[0], cells[1]
        if key == "属性" or key.startswith("---"):
            continue
        if key == "必选":
            props["required"] = val == "是"
        elif key == "多选":
            props["multi_select"] = val == "是"
        elif key == "主组":
            props["primary"] = val == "是"
        elif key == "维保组":
            props["maintenance_group"] = val == "是"
        elif key == "最大数量":
            try:
                props["max_quantity"] = int(val)
            except ValueError:
                props["max_quantity"] = 0
    return props


def _parse_module_table(lines: List[str]) -> List[Module]:
    """解析模块表格，返回模块列表"""
    modules: List[Module] = []
    header_found = False
    for line in lines:
        line = line.strip()
        if not line.startswith("|"):
            continue
        if not header_found:
            if "名称" in line and "型号" in line:
                header_found = True
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) < 9:
            continue
        # Skip separator rows (contain only dashes)
        if all(cell.startswith("-") and cell.endswith("-") for cell in cells):
            continue
        modules.append(Module(
            name=cells[0],
            model=cells[1],
            description=cells[2],
            unit=cells[3] or "个",
            price=parse_price(cells[4]),
            max_quantity=int(cells[5]) if cells[5].isdigit() else 0,
            discountable=cells[6] == "是",
            customizable=cells[7] == "是",
            notes=cells[8] if len(cells) > 8 else "",
        ))
    return modules


def _infer_module_category(group_name: str) -> ModuleCategory:
    """从模块组名称推断模块类别"""
    name_lower = group_name.lower()
    if "扩容" in group_name or "扩展" in name_lower:
        return ModuleCategory.EXPANSION
    if "增值" in group_name or "功能" in group_name:
        return ModuleCategory.VALUE_ADDED
    if "国产化" in group_name or "国产" in group_name:
        return ModuleCategory.LOCALIZATION
    if "部署" in group_name:
        return ModuleCategory.DEPLOYMENT
    if "维保" in group_name:
        return ModuleCategory.SUPPORT
    if "升级" in group_name:
        return ModuleCategory.UPGRADE
    if "探针" in group_name:
        return ModuleCategory.PROBE
    if "引擎" in group_name:
        return ModuleCategory.ENGINE
    return ModuleCategory.OTHER


# 产品名到类别的映射
_PRODUCT_CATEGORY_MAP: Dict[str, ProductCategory] = {
    "雷池": ProductCategory.WAF,
    "牧云": ProductCategory.HOST_SECURITY,
    "洞鉴": ProductCategory.VULN_SCANNER,
    "谛听": ProductCategory.DECEPTION,
    "全悉": ProductCategory.NDR,
    "API": ProductCategory.API_SECURITY,
    "慧鉴": ProductCategory.CODE_SECURITY,
    "码力": ProductCategory.CODE_DEVELOPMENT,
    "云图": ProductCategory.ASSET,
    "万象": ProductCategory.SOC,
}


def parse_product_markdown(content: str, filename: str = "") -> Product:
    """解析单个产品 Markdown 内容"""
    lines = content.split("\n")

    # 提取产品名
    product_name = ""
    product_id = ""
    for line in lines[:10]:
        if line.startswith("# ") and not product_name:
            product_name = line.replace("#", "").strip()
            product_name = re.sub(r"\s*产品清单\s*$", "", product_name)
        if "产品ID" in line:
            m = re.search(r"\*\*产品ID\*\*[：:]\s*(\S+)", line)
            if m:
                product_id = m.group(1)

    category = _PRODUCT_CATEGORY_MAP.get(product_name, ProductCategory.WAF)
    product = Product(name=product_name, product_id=product_id, category=category)

    # 解析软件版和硬件版区域
    current_section = None  # 'software' or 'hardware'
    current_version: Dict[str, Any] | None = None
    current_group_name: str = ""
    in_property_table: bool = False
    in_module_table: bool = False
    property_lines: List[str] = []
    module_lines: List[str] = []
    version_list_started: bool = False
    version_names: List[Dict[str, str]] = []
    software_version_names: List[Dict[str, str]] = []
    hardware_version_names: List[Dict[str, str]] = []

    def _flush_module_group():
        nonlocal in_property_table, in_module_table, property_lines, module_lines
        if not current_version or not current_group_name:
            property_lines = []
            module_lines = []
            in_property_table = False
            in_module_table = False
            return
        props = _parse_property_table(property_lines)
        modules = _parse_module_table(module_lines)
        if modules:
            for m in modules:
                m.category = _infer_module_category(current_group_name)
            group = ModuleGroup(
                name=current_group_name,
                modules=modules,
                required=props["required"],
                primary=props["primary"],
                multi_select=props["multi_select"],
                maintenance_group=props["maintenance_group"],
                max_quantity=props["max_quantity"],
            )
            current_version.setdefault("module_groups", []).append(group)
        property_lines = []
        module_lines = []
        in_property_table = False
        in_module_table = False

    def _flush_version():
        nonlocal current_version
        if not current_version:
            return
        _flush_module_group()
        version_type = current_version.get("version_type", "software")
        version_name = current_version.get("name", "")
        # 使用正确的 version_id
        correct_id = ""
        correct_number = 0
        name_list = software_version_names if version_type == "software" else hardware_version_names
        for vn in name_list:
            if vn["name"] == version_name:
                correct_id = vn["id"]
                correct_number = vn["number"]
                break
        current_version["version_id"] = correct_id or current_version.get("version_id", "")
        current_version["version_number"] = correct_number or current_version.get("version_number", 0)

        if version_type == "software":
            v = SoftwareVersion(**{k: v for k, v in current_version.items() if k != "version_type"})
            product.software_versions.append(v)
        else:
            v = HardwareVersion(**{k: v for k, v in current_version.items() if k != "version_type"})
            product.hardware_versions.append(v)
        current_version = None

    # 逐行解析
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # 检测分区标题
        if line.startswith("## 软件版"):
            if current_version:
                _flush_version()
            current_section = "software"
            software_version_names = []
            version_list_started = False
            i += 1
            continue
        elif line.startswith("## 硬件版"):
            if current_version:
                _flush_version()
            current_section = "hardware"
            hardware_version_names = []
            version_list_started = False
            i += 1
            continue

        # 版本对比表格
        if line.startswith("### 版本对比"):
            version_list_started = True
            version_names = []
            i += 1
            continue

        if version_list_started and line.startswith("|") and "版本名称" in line:
            # 表头，跳过
            i += 1
            # 跳过分隔符行
            if i < len(lines) and "---" in lines[i]:
                i += 1
            # 读取版本行
            while i < len(lines):
                row = lines[i].strip()
                if not row.startswith("|"):
                    break
                cells = [c.strip() for c in row.split("|")[1:-1]]
                if len(cells) >= 3:
                    entry = {"name": cells[0], "number": int(cells[1]) if cells[1].isdigit() else 0, "id": cells[2].strip("`")}
                    version_names.append(entry)
                    if current_section == "software":
                        software_version_names.append(entry)
                    elif current_section == "hardware":
                        hardware_version_names.append(entry)
                i += 1
            version_list_started = False
            continue

        # 版本详情标题: ### 软件版 N: 版本名 或 ### 硬件版 N: 版本名
        ver_match = re.match(r"###\s+(软件版|硬件版)\s+\d+[：:]\s*(.+)", line)
        if ver_match:
            _flush_version()
            ver_type = "software" if "软件" in ver_match.group(1) else "hardware"
            current_version = {
                "name": ver_match.group(2).strip(),
                "version_id": "",
                "version_number": 0,
                "version_type": ver_type,
            }
            current_section = ver_type
            i += 1
            continue

        # 版本元数据行: 跳过后继续检查
        if current_version and ("版本号" in line or "版本ID" in line):
            # 这些信息已通过版本对比表获取，跳过
            i += 1
            continue

        # 模块组标题: #### 模块组名
        group_match = re.match(r"####\s+(.+)", line)
        if group_match and current_version:
            _flush_module_group()
            current_group_name = group_match.group(1).strip()
            property_lines = []
            module_lines = []
            in_property_table = False
            in_module_table = False
            i += 1
            continue

        # 表格行检测
        if line.startswith("|") and current_version and current_group_name:
            # 判断是属性表还是模块表
            if "属性" in line and "值" in line:
                in_property_table = True
                in_module_table = False
            elif "名称" in line and "型号" in line:
                in_property_table = False
                in_module_table = True
            if in_property_table:
                property_lines.append(line)
            elif in_module_table:
                module_lines.append(line)
            i += 1
            continue

        i += 1

    # 处理最后一个版本
    _flush_version()

    return product


def parse_all_products(data_dir: str = "data") -> List[Product]:
    """解析 data/ 目录下所有产品 Markdown 文件"""
    products: List[Product] = []
    md_files = sorted(
        [f for f in os.listdir(data_dir) if f.endswith(".md") and f != "README.md"],
    )
    for filename in md_files:
        filepath = os.path.join(data_dir, filename)
        with open(filepath) as f:
            content = f.read()
        product = parse_product_markdown(content, filename=filename)
        products.append(product)
    return products


# ──────────────────────────────────────────────
#  产品缓存
# ──────────────────────────────────────────────

_cache_store: dict = {}  # {data_dir: (products, timestamp)}


def get_cached_products(data_dir: str = "data", ttl_seconds: int = 300) -> List[Product]:
    """获取缓存的产品列表，过期则重新解析"""
    import time as _time
    now = _time.time()
    entry = _cache_store.get(data_dir)
    if entry:
        products, ts = entry
        if now - ts < ttl_seconds:
            return products
    products = parse_all_products(data_dir)
    _cache_store[data_dir] = (products, now)
    return products


def clear_cache(data_dir: str = None) -> None:
    """清除缓存，不传 data_dir 则清除全部"""
    if data_dir:
        _cache_store.pop(data_dir, None)
    else:
        _cache_store.clear()