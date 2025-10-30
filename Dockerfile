# 使用一个轻量的 Python 官方镜像作为基础
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖，主要是 msmtp
RUN apt-get update && apt-get install -y msmtp ca-certificates && rm -rf /var/lib/apt/lists/*

# 复制 Python 依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制源码
COPY ./src .

# 设置容器启动时要执行的命令
# -u 参数确保日志能实时输出
CMD ["python", "-u", "telegram_to_email.py"]
