"""Streamlit 前端 - 安全产品智能选型助手 (平台集成版)

支持对话模式和表单模式，调用 ProductSelectorAgent。
嵌入在西南协作平台中，作为子页面展示。
"""
import streamlit as st
from product_selector.agent import ProductSelectorAgent
from product_selector.models import ProductCategory
from product_selector.intent import extract_requirements

CATEGORY_LABELS = {
    ProductCategory.WAF: "雷池 - Web应用防火墙",
    ProductCategory.HOST_SECURITY: "牧云 - 主机安全",
    ProductCategory.VULN_SCANNER: "洞鉴 - 漏洞扫描",
    ProductCategory.DECEPTION: "谛听 - 蜜罐诱捕",
    ProductCategory.NDR: "全悉 - 流量分析(NDR)",
    ProductCategory.API_SECURITY: "API安全",
    ProductCategory.CODE_SECURITY: "慧鉴 - 静态代码安全测试(SAST)",
    ProductCategory.CODE_DEVELOPMENT: "码力 - AI智能开发平台",
    ProductCategory.ASSET: "云图 - 资产管理",
    ProductCategory.SOC: "万象 - 安全分析与运营平台",
}

CATEGORY_HINTS = {
    ProductCategory.WAF: ("QPS 需求", "需要防护多大 QPS？", "qps"),
    ProductCategory.HOST_SECURITY: ("节点数", "需要管理多少台服务器/节点？", "nodes"),
    ProductCategory.VULN_SCANNER: ("扫描引擎数", "需要多少个扫描引擎节点？", "engines"),
    ProductCategory.DECEPTION: ("蜜罐数量", "需要部署多少个蜜罐？", "honeypots"),
    ProductCategory.NDR: ("流量 (Mbps)", "需要分析多大流量？", "mbps"),
    ProductCategory.API_SECURITY: ("QPS 需求", "需要防护多大 QPS？", "qps"),
    ProductCategory.CODE_SECURITY: ("并发任务数", "需要多少个并发扫描任务？", "concurrency"),
    ProductCategory.CODE_DEVELOPMENT: ("AI并发数", "需要多少个AI员工并发？", "concurrency"),
    ProductCategory.ASSET: (None, None, None),
    ProductCategory.SOC: ("日均EPS", "日均日志量(EPS)？", "eps"),
}

NEEDS_DEPLOYMENT = {
    ProductCategory.WAF: True,
    ProductCategory.HOST_SECURITY: True,
    ProductCategory.VULN_SCANNER: False,
    ProductCategory.DECEPTION: False,
    ProductCategory.NDR: True,
    ProductCategory.API_SECURITY: True,
    ProductCategory.CODE_SECURITY: False,
    ProductCategory.CODE_DEVELOPMENT: False,
    ProductCategory.ASSET: True,
    ProductCategory.SOC: True,
}

DEPLOYMENT_OPTIONS_BY_PRODUCT = {
    ProductCategory.WAF: ["单机部署", "集群部署", "K8s部署"],
    ProductCategory.HOST_SECURITY: ["单机部署", "分布式集群部署"],
    ProductCategory.NDR: ["单机部署", "集群部署", "旁路部署"],
    ProductCategory.API_SECURITY: ["单机部署", "集群部署"],
    ProductCategory.ASSET: ["一体化部署", "管端分离部署"],
    ProductCategory.SOC: ["单机部署", "集群部署"],
}

DEPLOYMENT_OPTIONS = ["单机部署", "集群部署", "K8s部署", "旁路部署", "不限"]


# ============================================================
# 页面配置与隐藏 Streamlit 默认元素
# ============================================================
st.set_page_config(
    page_title="产品选型 - 西南协作平台",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

hide_streamlit_style = """
<style>
  #MainMenu {visibility: hidden !important;}
  header {visibility: hidden !important;}
  footer {visibility: hidden !important;}
  .stAppToolbar {display: none !important;}
  .st-emotion-cache-zq5wmm {display: none !important;}
  .stAppDeployButton {display: none !important;}
  div[data-testid="stDecoration"] {display: none !important;}
  section[data-testid="stSidebar"] {display: none !important;}

  /* 平台导航栏 */
  .platform-header {
    background: linear-gradient(135deg, #1a73e8 0%, #0d47a1 100%);
    padding: 16px 24px;
    border-radius: 8px;
    margin-bottom: 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .platform-header .back-link {
    color: white;
    text-decoration: none;
    font-size: 14px;
    opacity: 0.85;
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .platform-header .back-link:hover {opacity: 1;}
  .platform-header h2 {
    color: white;
    font-size: 18px;
    font-weight: 500;
    margin: 0;
  }
  .platform-header .header-badge {
    color: rgba(255,255,255,0.7);
    font-size: 12px;
    background: rgba(255,255,255,0.15);
    padding: 2px 10px;
    border-radius: 12px;
  }
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# 平台导航栏
st.markdown(f"""
<div class="platform-header">
  <a href="/" target="_self" class="back-link">← 返回西南协作平台</a>
  <h2>安全产品智能选型</h2>
  <span class="header-badge">长亭科技</span>
</div>
""", unsafe_allow_html=True)


# ============================================================
# Agent 与 Session
# ============================================================
@st.cache_resource
def get_agent() -> ProductSelectorAgent:
    from product_selector.config import SelectorConfig
    config = SelectorConfig.from_env(data_dir="data")
    return ProductSelectorAgent(data_dir="data", config=config)


def init_session():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "agent_session_id" not in st.session_state:
        st.session_state.agent_session_id = "streamlit"
    if "form_result" not in st.session_state:
        st.session_state.form_result = None
    if "module_selections" not in st.session_state:
        st.session_state.module_selections = {}
    if "form_requirements_key" not in st.session_state:
        st.session_state.form_requirements_key = None


# ============================================================
# 推荐方案渲染
# ============================================================
def render_recommendation(result: dict):
    data = result["data"]
    primary = data["primary_recommendation"]

    st.success(f"推荐方案: **{primary['product']} {primary['version']}**")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("基础价格", f"¥{primary['base_price']}")
    with col2:
        st.metric("配置总价", f"¥{data['total_price']}")
    with col3:
        st.metric(
            "折后价格",
            f"¥{data['discount_min_price']} ~ ¥{data['discount_max_price']}",
        )

    st.caption(f"折扣范围: {data['discount_range'][0]} ~ {data['discount_range'][1]}")

    if primary["selected_modules"]:
        with st.expander("选配模块", expanded=True):
            for m in primary["selected_modules"]:
                st.write(f"- **{m['name']}** ({m['model']}): ¥{m['price']}")

    with st.expander("推荐理由", expanded=True):
        st.write(data["summary"])
        st.info(primary["reasoning"])

    if data.get("alternatives"):
        with st.expander("备选方案"):
            for alt in data["alternatives"]:
                st.write(f"- **{alt['product']} {alt['version']}**: ¥{alt['subtotal_price']} — {alt['reasoning']}")

    if data.get("additional_suggestions"):
        with st.expander("补充建议"):
            for s in data["additional_suggestions"]:
                st.write(f"- {s}")


def render_recommendation_with_modules(result: dict):
    data = result["data"]
    primary = data["primary_recommendation"]
    available_modules = data.get("available_modules", [])

    st.success(f"推荐方案: **{primary['product']} {primary['version']}**")

    if "module_selections" not in st.session_state:
        st.session_state.module_selections = {}

    col1, col2, col3 = st.columns(3)
    base_price = primary.get("base_price", 0)
    initial_total = data.get("total_price", 0)

    with col1:
        st.metric("基础价格", f"¥{base_price}")
    with col2:
        st.metric("初始配置总价", f"¥{initial_total}")
    with col3:
        st.metric(
            "折后价格",
            f"¥{data['discount_min_price']} ~ ¥{data['discount_max_price']}",
        )

    st.caption(f"折扣范围: {data['discount_range'][0]} ~ {data['discount_range'][1]}")

    if primary["selected_modules"]:
        with st.expander("已包含模块", expanded=True):
            for m in primary["selected_modules"]:
                qty = m.get("quantity", 1)
                total = m["price"] * qty
                st.write(f"- **{m['name']}** ({m['model']}): ¥{m['price']} × {qty} = ¥{total}")

    with st.expander("推荐理由", expanded=True):
        st.write(data["summary"])
        st.info(primary["reasoning"])

    if available_modules:
        with st.expander("模块选配（可选）", expanded=True):
            st.caption("勾选需要的模块，实时更新价格")

            from decimal import Decimal
            added_price = Decimal("0")
            selected_modules_list = []

            for group in available_modules:
                group_name = group.get("name", "")
                group_max_qty = group.get("max_quantity", 0)

                st.markdown(f"**{group_name}**")

                for module in group.get("modules", []):
                    mod_key = f"mod_{module['model']}"
                    mod_name = module.get("name", "")
                    mod_price = Decimal(str(module.get("price", 0)))
                    mod_max_qty = module.get("max_quantity", 1)
                    can_multi = mod_max_qty > 1 or group_max_qty > 1

                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        selected = st.checkbox(
                            f"{mod_name} (¥{mod_price})",
                            key=mod_key,
                            value=st.session_state.module_selections.get(mod_key, {}).get("selected", False),
                        )
                    with col2:
                        if selected and can_multi:
                            max_qty = max(mod_max_qty, group_max_qty) if group_max_qty > 0 else mod_max_qty
                            qty = st.number_input(
                                "数量",
                                min_value=1,
                                max_value=max_qty if max_qty > 0 else 100,
                                value=st.session_state.module_selections.get(mod_key, {}).get("quantity", 1),
                                key=f"{mod_key}_qty",
                            )
                        else:
                            qty = 1
                    with col3:
                        if selected:
                            item_total = mod_price * qty
                            added_price += item_total
                            selected_modules_list.append({
                                "name": mod_name,
                                "model": module.get("model", ""),
                                "price": mod_price,
                                "quantity": qty,
                            })
                            st.write(f"+¥{item_total}")

                    st.session_state.module_selections[mod_key] = {
                        "selected": selected,
                        "quantity": qty if selected else 1,
                    }

                st.divider()

            final_total = Decimal(str(initial_total)) + added_price
            st.metric("选配后总价", f"¥{final_total}")

            if selected_modules_list:
                st.caption("已选配模块:")
                for m in selected_modules_list:
                    st.write(f"- {m['name']}: ¥{m['price']} × {m['quantity']} = ¥{m['price'] * m['quantity']}")

    if data.get("alternatives"):
        with st.expander("备选方案"):
            for alt in data["alternatives"]:
                st.write(f"- **{alt['product']} {alt['version']}**: ¥{alt['subtotal_price']} — {alt['reasoning']}")

    if data.get("additional_suggestions"):
        with st.expander("补充建议"):
            for s in data["additional_suggestions"]:
                st.write(f"- {s}")


# ============================================================
# 对话模式
# ============================================================
def dialogue_tab():
    st.subheader("对话模式")
    st.caption("用自然语言描述需求，Agent 会逐步引导您完善信息并推荐方案。")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if msg["role"] == "user":
                st.write(msg["content"])
            else:
                if isinstance(msg["content"], dict) and msg["content"].get("type") == "recommendation":
                    render_recommendation_with_modules(msg["content"])
                else:
                    st.write(msg["content"])

    user_input = st.chat_input("描述您的需求...", key="chat_input")
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        agent = get_agent()
        result = agent.process_with_session(user_input, st.session_state.agent_session_id)
        st.session_state.messages.append({"role": "agent", "content": result})
        if result["type"] == "recommendation":
            agent.clear_session(st.session_state.agent_session_id)
        st.rerun()

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("重新开始", use_container_width=True):
            get_agent().clear_session(st.session_state.agent_session_id)
            st.session_state.messages = []
            st.rerun()


# ============================================================
# 表单模式
# ============================================================
def form_tab():
    st.subheader("表单模式")
    st.caption("通过表单快速填写需求，一键生成推荐方案。")

    col1, col2 = st.columns(2)
    with col1:
        cat_label = st.selectbox(
            "产品类型",
            options=[""] + list(CATEGORY_LABELS.values()),
            key="form_category",
        )
    selected_cat = None
    for cat, label in CATEGORY_LABELS.items():
        if label == cat_label:
            selected_cat = cat
            break

    version_type = None
    if selected_cat:
        with col2:
            version_type_str = st.radio(
                "版本类型",
                options=["不限", "软件版", "硬件版"],
                horizontal=True,
                key="form_version_type",
            )
            version_type_map = {"不限": None, "软件版": "software", "硬件版": "hardware"}
            version_type = version_type_map.get(version_type_str)

    hint = CATEGORY_HINTS.get(selected_cat) if selected_cat else None

    col_left, col_right = st.columns(2)
    performance_value = None
    if hint and hint[0] is not None:
        with col_left:
            performance_value = st.number_input(
                hint[0], min_value=0, step=100, value=0,
                help=hint[1],
                key="form_perf",
            )

    deployment = None
    if selected_cat and NEEDS_DEPLOYMENT.get(selected_cat, False):
        deploy_options = DEPLOYMENT_OPTIONS_BY_PRODUCT.get(selected_cat, DEPLOYMENT_OPTIONS)
        with col_left:
            deployment = st.selectbox(
                "部署方式", options=["不限"] + deploy_options,
                key="form_deploy",
            )
    with col_right:
        localization = st.checkbox("需要国产化/信创", key="form_local")
        ha_required = st.checkbox("需要高可用", key="form_ha")

    if selected_cat == ProductCategory.HOST_SECURITY:
        st.info("💡 牧云产品需配备探针模块，探针数量将根据节点数自动计算")

    submitted = st.button("生成推荐方案", type="primary", use_container_width=True)

    req_key = f"{selected_cat}_{version_type}_{performance_value}_{deployment}_{localization}_{ha_required}"

    if submitted:
        if not selected_cat:
            st.warning("请选择产品类型")
            st.session_state.form_result = None
            return

        agent = get_agent()
        requirements = extract_requirements(cat_label)
        requirements.product_category = selected_cat

        if version_type:
            from product_selector.models import VersionType
            requirements.version_type = VersionType(version_type)

        if hint and hint[2] and performance_value:
            perf_key_map = {
                "qps": "qps_requirement",
                "nodes": "node_count",
                "engines": "engine_count",
                "honeypots": "honeypot_count",
                "mbps": "mbps_requirement",
                "assets": "asset_count",
                "concurrency": "concurrency_count",
                "eps": "eps_requirement",
            }
            key = perf_key_map.get(hint[2])
            if key:
                setattr(requirements, key, performance_value)

        if deployment and deployment != "不限":
            requirements.deployment_mode = deployment

        requirements.localization_required = localization
        requirements.ha_required = ha_required

        if not requirements.is_complete():
            st.warning(f"请补充以下信息: {'、'.join(requirements.missing_fields())}")
            st.session_state.form_result = None
            return

        from product_selector.reasoning import recommend
        result = recommend(agent.products, requirements)
        if result is None:
            st.error("未找到匹配的产品方案，请调整需求。")
            st.session_state.form_result = None
            return

        st.session_state.form_result = {
            "type": "recommendation",
            "data": agent._serialize_result(result),
        }
        st.session_state.form_requirements_key = req_key
        st.session_state.module_selections = {}

    if st.session_state.form_result:
        st.divider()
        st.success("推荐方案已生成")
        render_recommendation_with_modules(st.session_state.form_result)


# ============================================================
# 主入口
# ============================================================
def main():
    init_session()
    tab1, tab2 = st.tabs(["对话模式", "表单模式"])
    with tab1:
        dialogue_tab()
    with tab2:
        form_tab()


if __name__ == "__main__":
    main()
