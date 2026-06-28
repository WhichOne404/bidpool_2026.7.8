"""安全产品智能选型助手 - Pydantic v2 数据模型"""
from typing import List, Optional, Dict, Any, Tuple
from decimal import Decimal
from pydantic import BaseModel, Field, model_validator
from enum import Enum


class ProductCategory(str, Enum):
    WAF = "WAF"
    HOST_SECURITY = "host_security"
    VULN_SCANNER = "vuln_scanner"
    DECEPTION = "deception"
    NDR = "ndr"
    API_SECURITY = "api_security"
    CODE_SECURITY = "code_security"  # 慧鉴 - SAST
    CODE_DEVELOPMENT = "code_development"  # 码力 - AI编程
    ASSET = "asset"  # 云图 - 资产管理
    SOC = "soc"  # 万象 - 安全运营平台


class VersionType(str, Enum):
    """版本类型：软件版或硬件版"""
    SOFTWARE = "software"
    HARDWARE = "hardware"


class ModuleCategory(str, Enum):
    BASE = "base"
    EXPANSION = "expansion"
    VALUE_ADDED = "value_added"
    LOCALIZATION = "localization"
    DEPLOYMENT = "deployment"
    SUPPORT = "support"
    UPGRADE = "upgrade"
    PROBE = "probe"
    ENGINE = "engine"
    OTHER = "other"


class Module(BaseModel):
    """产品模块/配件"""
    name: str = Field(..., description="模块名称")
    model: str = Field(..., description="型号")
    description: str = Field(..., description="描述")
    price: Decimal = Field(..., ge=0, description="单价")
    unit: str = Field(default="个", description="单位")
    max_quantity: int = Field(default=0, ge=0, description="最大数量，0表示不限")
    discountable: bool = Field(default=True, description="是否可打折")
    customizable: bool = Field(default=False, description="是否定制")
    category: ModuleCategory = Field(default=ModuleCategory.BASE, description="模块类别")
    notes: str = Field(default="", description="备注说明")


class ModuleGroup(BaseModel):
    """模块组"""
    name: str = Field(..., description="组名称")
    modules: List[Module] = Field(default_factory=list, description="包含的模块列表")
    required: bool = Field(default=False, description="是否必选")
    primary: bool = Field(default=False, description="是否为主组(基础产品组)")
    multi_select: bool = Field(default=False, description="是否允许多选")
    maintenance_group: bool = Field(default=False, description="是否为维保组")
    max_quantity: int = Field(default=0, ge=0, description="组最大数量，0表示不限")


class CapacitySpec(BaseModel):
    """容量规格"""
    max_qps: Optional[int] = Field(None, description="最大QPS (雷池)")
    max_nodes: Optional[int] = Field(None, description="最大节点数 (牧云)")
    max_mbps: Optional[int] = Field(None, description="最大流量Mbps (全悉)")
    max_honeypots: Optional[int] = Field(None, description="最大蜜罐数 (谛听)")
    max_assets: Optional[int] = Field(None, description="最大资产数 (万象/云图)")
    max_engines: Optional[int] = Field(None, description="最大引擎数 (洞鉴)")


class Version(BaseModel):
    """版本基类"""
    name: str = Field(..., description="版本名称")
    version_id: str = Field(..., description="版本ID")
    version_number: int = Field(..., description="版本号")
    version_type: str = Field(default="software", description="版本类型: software/hardware")
    module_groups: List[ModuleGroup] = Field(default_factory=list, description="模块组列表")
    capacity: Optional[CapacitySpec] = Field(None, description="容量规格")
    description: str = Field(default="", description="版本描述")

    def get_base_module(self) -> Optional[Module]:
        """获取基础产品模块"""
        for group in self.module_groups:
            if group.primary and group.modules:
                return group.modules[0]
        return None

    def get_base_price(self) -> Decimal:
        """获取基础价格"""
        base = self.get_base_module()
        return base.price if base else Decimal("0")

    def get_optional_module_groups(self) -> List[ModuleGroup]:
        """获取可选模块组(非主组且非必选)"""
        return [g for g in self.module_groups if not g.primary and not g.required]

    def get_module_group_by_name(self, name: str) -> Optional[ModuleGroup]:
        """按名称查找模块组"""
        for g in self.module_groups:
            if g.name == name:
                return g
        return None


class SoftwareVersion(Version):
    """软件版本"""
    version_type: str = "software"
    deployment_modes: List[str] = Field(default_factory=list, description="支持的部署模式")


class HardwareVersion(Version):
    """硬件版本"""
    version_type: str = "hardware"
    hardware_spec: Dict[str, Any] = Field(default_factory=dict, description="硬件规格")


class Product(BaseModel):
    """产品"""
    name: str = Field(..., description="产品名称")
    product_id: str = Field(..., description="产品ID")
    category: ProductCategory = Field(..., description="产品类别")
    description: str = Field(default="", description="产品描述")
    key_features: List[str] = Field(default_factory=list, description="核心功能特点")
    software_versions: List[SoftwareVersion] = Field(default_factory=list)
    hardware_versions: List[HardwareVersion] = Field(default_factory=list)

    def get_all_versions(self) -> List[Version]:
        return self.software_versions + self.hardware_versions

    def get_software_version_by_name(self, name: str) -> Optional[SoftwareVersion]:
        for v in self.software_versions:
            if v.name == name:
                return v
        return None

    def get_hardware_version_by_name(self, name: str) -> Optional[HardwareVersion]:
        for v in self.hardware_versions:
            if v.name == name:
                return v
        return None


class UserRequirements(BaseModel):
    """用户需求"""
    product_category: Optional[ProductCategory] = Field(None, description="产品类型")
    product_name: Optional[str] = Field(None, description="指定产品名称")

    qps_requirement: Optional[int] = Field(None, ge=0, description="QPS需求")
    node_count: Optional[int] = Field(None, ge=0, description="节点数量")
    mbps_requirement: Optional[int] = Field(None, ge=0, description="流量Mbps需求")
    honeypot_count: Optional[int] = Field(None, ge=0, description="蜜罐数量")
    asset_count: Optional[int] = Field(None, ge=0, description="资产数量")
    engine_count: Optional[int] = Field(None, ge=0, description="引擎数量")
    concurrency_count: Optional[int] = Field(None, ge=0, description="并发数(慧鉴/码力)")
    eps_requirement: Optional[int] = Field(None, ge=0, description="日均EPS(万象)")

    deployment_mode: Optional[str] = Field(None, description="部署模式")
    ha_required: bool = Field(default=False, description="是否需要高可用")

    localization_required: bool = Field(default=False, description="是否需要国产化")
    os_type: Optional[str] = Field(None, description="操作系统类型")

    features_required: List[str] = Field(default_factory=list, description="需要的功能")

    budget_min: Optional[Decimal] = Field(None, ge=0, description="预算下限")
    budget_max: Optional[Decimal] = Field(None, ge=0, description="预算上限")

    # 新增字段：版本类型偏好和模块选配
    version_type: Optional[VersionType] = Field(None, description="版本类型偏好: software/hardware")
    selected_modules: List[Dict[str, Any]] = Field(default_factory=list, description="已选模块")

    notes: str = Field(default="", description="其他备注")

    def _has_performance_requirement(self) -> bool:
        return any([
            self.qps_requirement,
            self.node_count,
            self.mbps_requirement,
            self.honeypot_count,
            self.asset_count,
            self.engine_count,
            self.concurrency_count,
            self.eps_requirement,
        ])

    def _has_product_spec(self) -> bool:
        return self.product_category is not None or self.product_name is not None

    def is_complete(self) -> bool:
        # 基本条件：必须有产品类型
        if not self._has_product_spec():
            return False

        # 云图特殊处理：不需要性能参数，只需要产品类型
        # (部署模式和国产化是可选的)
        if self.product_category == ProductCategory.ASSET:
            return True

        # 其他产品：需要产品类型 + 性能参数
        return self._has_performance_requirement()

    def missing_fields(self) -> List[str]:
        missing = []
        if not self._has_product_spec():
            missing.append("产品类型/产品名称")
        if not self._has_performance_requirement():
            missing.append("性能/容量需求")
        return missing


class ProductConfig(BaseModel):
    """单个产品的配置推荐"""
    product: Product = Field(..., description="产品信息")
    version: Version = Field(..., description="推荐版本")
    selected_modules: List[Module] = Field(default_factory=list, description="选配模块")
    subtotal_price: Decimal = Field(..., description="小计价格")
    reasoning: str = Field(..., description="推荐理由")


class RecommendationResult(BaseModel):
    """推荐结果"""
    primary_recommendation: ProductConfig = Field(..., description="主推荐方案")
    alternatives: List[ProductConfig] = Field(default_factory=list, description="备选方案")
    total_price: Decimal = Field(..., description="总价")
    discount_range: Tuple[Decimal, Decimal] = Field(..., description="折扣范围 (最低, 最高)")
    summary: str = Field(..., description="推荐摘要")
    additional_suggestions: List[str] = Field(default_factory=list, description="额外建议")