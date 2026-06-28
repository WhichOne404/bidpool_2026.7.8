"""FastAPI 路由"""
from typing import Optional
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from product_selector.api.schemas import (
    RecommendRequest, RecommendResponse,
    ProductListResponse, ProductItem, HealthResponse,
)
from product_selector.parser import get_cached_products
from product_selector.agent import ProductSelectorAgent
from product_selector.config import SelectorConfig
from product_selector import __version__

app = FastAPI(
    title="安全产品智能选型助手",
    description="长亭科技安全产品智能选型 API",
    version=__version__,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 启动时加载产品数据（使用缓存避免重复解析）
_config = SelectorConfig.from_env(data_dir="data")
_products = get_cached_products("data", ttl_seconds=_config.cache_ttl_seconds)
_agent = ProductSelectorAgent(data_dir="data", config=_config)
_agent.products = _products  # 使用已加载的产品，避免二次解析


@app.get("/api/health", response_model=HealthResponse)
def health_check():
    llm = _agent._get_llm_client()
    vs = _agent._get_vector_store()
    return HealthResponse(
        status="ok",
        product_count=len(_products),
        version=__version__,
        llm_available=llm is not None and llm.available,
        vector_search_available=vs is not None and vs.available,
    )


@app.get("/api/products", response_model=ProductListResponse)
def list_products(category: Optional[str] = Query(None)):
    result = []
    for p in _products:
        if category and p.category.value != category:
            continue
        result.append(ProductItem(
            id=p.product_id,
            name=p.name,
            category=p.category.value,
            description=p.description or "",
            software_version_count=len(p.software_versions),
            hardware_version_count=len(p.hardware_versions),
        ))
    return ProductListResponse(products=result)


from fastapi import FastAPI, Query, HTTPException


@app.get("/api/products/{product_id}")
def get_product(product_id: str):
    for p in _products:
        if p.product_id == product_id:
            return {
                "id": p.product_id,
                "name": p.name,
                "category": p.category.value,
                "description": p.description,
                "key_features": p.key_features,
                "software_versions": [
                    {
                        "name": v.name,
                        "version_id": v.version_id,
                        "version_number": v.version_number,
                        "base_price": str(v.get_base_price()),
                        "deployment_modes": getattr(v, "deployment_modes", []),
                        "module_groups": [
                            {"name": g.name, "module_count": len(g.modules)}
                            for g in v.module_groups
                        ],
                    }
                    for v in p.software_versions
                ],
                "hardware_versions": [
                    {
                        "name": v.name,
                        "version_id": v.version_id,
                        "version_number": v.version_number,
                        "base_price": str(v.get_base_price()),
                        "hardware_spec": getattr(v, "hardware_spec", {}),
                    }
                    for v in p.hardware_versions
                ],
            }
    raise HTTPException(status_code=404, detail="Product not found")


@app.post("/api/recommend", response_model=RecommendResponse)
def recommend(request: RecommendRequest):
    if request.input_type == "form":
        from product_selector.intent import extract_requirements
        req_data = request.input
        requirements = extract_requirements(
            req_data.get("message", "") or str(req_data)
        )
    else:
        message = request.input.get("message", "")
        if not message:
            return RecommendResponse(
                status="error",
                type="question",
                question="请输入您的需求描述",
            ).model_dump()
        requirements = None
        from product_selector.intent import extract_requirements
        requirements = extract_requirements(message)

    result = _agent.process(
        request.input.get("message", "") if request.input_type == "dialogue"
        else str(request.input)
    )

    if request.session_id:
        result["session_id"] = request.session_id

    return result