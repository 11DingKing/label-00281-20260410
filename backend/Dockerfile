# 多架构支持 (amd64/arm64)
# 真正的离线部署 - 模型在构建时预下载
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
# 模型缓存目录
ENV HF_HOME=/app/.cache/huggingface
ENV PADDLE_HOME=/app/.paddleocr

# 安装系统依赖 (PaddleOCR 需要的依赖)
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libfontconfig1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 根据架构安装 PaddlePaddle (使用 2.6.2 稳定版)
ARG TARGETARCH
RUN pip install paddlepaddle==2.6.2 -i https://pypi.tuna.tsinghua.edu.cn/simple

# 安装其他Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制模型下载脚本
COPY scripts/download_models.py /app/scripts/

# ===== 关键：在构建时预下载所有模型 =====
# 这确保容器可以完全离线运行
RUN mkdir -p /app/.cache/huggingface /app/.paddleocr && \
    python /app/scripts/download_models.py

# 复制应用代码
COPY . .

# 创建必要的目录
RUN mkdir -p uploads results history

# 暴露端口
EXPOSE 5000

# 设置环境变量
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1
ENV DISABLE_MODEL_SOURCE_CHECK=True
ENV DOCKER_ENV=true
# 指定模型缓存路径
ENV HF_HOME=/app/.cache/huggingface
ENV PADDLE_HOME=/app/.paddleocr

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

# 使用 Gunicorn 生产级 WSGI 服务器启动应用
CMD ["gunicorn", "--config", "gunicorn.conf.py", "app:app"]
