FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制产品选型模块和数据
COPY product_selector/ /app/product_selector/
COPY data/ /app/data/
COPY .env /app/.env

EXPOSE 8000

CMD ["uvicorn", "product_selector.api.routes:app", "--host", "0.0.0.0", "--port", "8000"]
