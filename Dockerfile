# ==========================================
# Stage 1: Builder (编译阶段)
# ==========================================
FROM python:3.10-slim as builder

WORKDIR /app

# 安装系统级依赖 (编译某些 C 扩展库需要，如 numpy/pandas)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt ./

# 创建虚拟环境并安装依赖
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
#RUN pip install --upgrade pip && \
#    pip install --no-cache-dir -r requirements.txt
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
#RUN pip install --upgrade pip && \
#    pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# ==========================================
# Stage 2: Runtime (运行阶段)
# ==========================================
FROM python:3.10-slim

WORKDIR /app

# 只要从 builder 阶段把装好的包复制过来就行
COPY --from=builder /opt/venv /opt/venv

# 设置环境变量
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# 复制业务代码
COPY ./app ./app

# 创建非 root 用户运行 (安全最佳实践)
RUN useradd -m myuser

# 这样 myuser 才能在运行时创建 model_cache 目录
RUN chown -R myuser:myuser /app

USER myuser

# 暴露端口
EXPOSE 8080

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
