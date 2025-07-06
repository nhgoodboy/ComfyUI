# 使用官方Python镜像作为基础镜像
FROM python:3.11-slim

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    APP_ENV=production

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get autoremove -y

# 创建非root用户（提前创建，提高安全性）
RUN groupadd -r appgroup && useradd -r -g appgroup -u 1000 appuser

# 创建必要的目录并设置权限
RUN mkdir -p /app/logs /app/temp && \
    chown -R appuser:appgroup /app

# 复制requirements.txt并安装依赖（利用Docker缓存层）
COPY --chown=appuser:appgroup requirements.txt .

# 升级pip并安装Python依赖
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY --chown=appuser:appgroup . .

# 确保启动脚本具有执行权限
RUN chmod +x start.py

# 切换到非root用户
USER appuser

# 暴露端口
EXPOSE 8000

# 添加标签
LABEL maintainer="Style Transform API Team" \
      version="1.0.0" \
      description="Style Transform API based on ComfyUI"

# 健康检查（更详细的检查）
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 设置默认环境变量
ENV HOST=0.0.0.0 \
    PORT=8000 \
    WORKERS=1 \
    LOG_LEVEL=INFO

# 创建卷挂载点（用于日志和临时文件）
VOLUME ["/app/logs", "/app/temp"]

# 启动命令（使用优化的启动脚本）
CMD ["python", "start.py", "--host", "0.0.0.0", "--port", "8000"] 