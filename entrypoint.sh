#!/bin/sh

# 检查必要的环境变量是否存在
if [ -z "$MSMTP_HOST" ] || [ -z "$MSMTP_USER" ] || [ -z "$MSMTP_PASSWORD" ] || [ -z "$MSMTP_FROM" ]; then
  echo "错误：一个或多个 msmtp 环境变量未设置。"
  echo "请在 docker-compose.yml 中定义 MSMTP_HOST, MSMTP_USER, MSMTP_PASSWORD, 和 MSMTP_FROM。"
  exit 1
fi

# 使用环境变量动态创建 /etc/msmtprc 文件
# cat <<EOF 是一个创建多行文本的好方法
cat <<EOF > /etc/msmtprc
# 此文件由 entrypoint.sh 自动生成
defaults
auth           on
tls            on
tls_trust_file /etc/ssl/certs/ca-certificates.crt
logfile        /dev/stdout

account        default
host           ${MSMTP_HOST}
port           ${MSMTP_PORT:-587} # 如果 MSMTP_PORT 未设置，则默认为 587
from           ${MSMTP_FROM}
user           ${MSMTP_USER}
password       ${MSMTP_PASSWORD}
EOF

# 设置文件权限，确保只有所有者可读
chmod 600 /etc/msmtprc

# 执行 Dockerfile 中 CMD 定义的命令 (即启动 Python 脚本)
# "$@" 允许我们传递额外的参数给 python 脚本
exec "$@"
