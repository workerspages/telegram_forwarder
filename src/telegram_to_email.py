import asyncio
import os
import sys
from io import BytesIO
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from telethon import TelegramClient, events
from telethon.tl.types import DocumentAttributeFilename

# --- 1. 从环境变量中读取配置 ---

def get_env_var(var_name, is_int=False, is_list=False):
    """一个辅助函数,用于安全地从环境变量获取配置"""
    value = os.getenv(var_name)
    if value is None:
        print(f"错误:环境变量 {var_name} 未设置。请在 docker-compose.yml 中定义它。")
        sys.exit(1)
    if is_int:
        return int(value)
    if is_list:
        return [int(x.strip()) for x in value.split(',')]
    return value

try:
    API_ID = get_env_var('API_ID', is_int=True)
    API_HASH = get_env_var('API_HASH')
    SESSION_NAME = get_env_var('SESSION_NAME')
    TARGET_CHAT_IDS = get_env_var('TARGET_CHAT_IDS', is_list=True)
    TO_EMAIL = get_env_var('TO_EMAIL')
except (ValueError, TypeError) as e:
    print(f"配置解析错误: {e}. 请检查 docker-compose.yml 中的环境变量格式。")
    sys.exit(1)


# --- 2. 邮件发送的核心逻辑 ---

async def send_email(subject, body_text, attachment=None, filename=None):
    """一个独立的函数,负责将内容发送到邮箱"""
    mime_msg = MIMEMultipart()
    mime_msg['From'] = TO_EMAIL
    mime_msg['To'] = TO_EMAIL
    mime_msg['Subject'] = subject
    mime_msg.attach(MIMEText(body_text, 'plain', 'utf-8'))

    if attachment and filename:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment)
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment', filename=filename)
        mime_msg.attach(part)

    raw_bytes = mime_msg.as_bytes()
    proc = await asyncio.create_subprocess_exec(
        'msmtp', '-t',
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate(input=raw_bytes)

    if proc.returncode == 0:
        print(f"成功转发邮件 (标题: {subject}) 到 {TO_EMAIL}")
    else:
        print(f"邮件转发失败: {stderr.decode()}")


# --- 3. 辅助函数:安全获取文件名 ---

def get_filename_from_document(document):
    """从 Telegram Document 的 attributes 中提取文件名"""
    if hasattr(document, 'attributes'):
        for attr in document.attributes:
            if isinstance(attr, DocumentAttributeFilename):
                return attr.file_name
    return None


# --- 4. Telethon 客户端和事件处理 ---

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

@client.on(events.NewMessage(chats=TARGET_CHAT_IDS))
async def message_handler(event):
    """当在指定群组中收到新消息时,此函数会被自动调用。"""
    msg = event.message
    print(f"--- 收到新消息 (ID: {msg.id}) ---")

    # 1. 获取发送者信息
    sender_info = "未知来源"
    try:
        sender = await msg.get_sender()
        if sender:
            sender_info = f"用户: {sender.first_name or ''}"
            if sender.last_name:
                sender_info += f" {sender.last_name}"
            if sender.username:
                sender_info += f" (@{sender.username})"
        elif msg.chat:
            sender_info = f"来自群组/频道: {msg.chat.title}"
    except Exception as e:
        print(f"获取发送者信息时出错: {e}")

    # 2. 构建邮件正文
    body_text = (
        f"From: {sender_info}\n\n"
        + (msg.text or "[无文本内容]")
    )

    # 3. 根据消息类型确定邮件标题和附件
    subject = "【Telegram】新消息"
    attachment_data = None
    attachment_filename = None

    try:
        if msg.photo:
            subject = "【Telegram】新图片信息"
            attachment_data = await msg.download_media(file=bytes)
            attachment_filename = f"image_{msg.id}.jpg"
            
        elif msg.document:
            subject = "【Telegram】新附件信息"
            attachment_data = await msg.download_media(file=bytes)
            # 安全地获取文件名
            attachment_filename = get_filename_from_document(msg.document) or f"file_{msg.id}"
            
        elif msg.video:
            subject = "【Telegram】新视频信息"
            attachment_data = await msg.download_media(file=bytes)
            # 尝试从 video attributes 获取文件名
            attachment_filename = get_filename_from_document(msg.video) or f"video_{msg.id}.mp4"
            
        elif msg.voice:
            subject = "【Telegram】新语音信息"
            attachment_data = await msg.download_media(file=bytes)
            attachment_filename = f"voice_{msg.id}.ogg"
            
        elif msg.audio:
            subject = "【Telegram】新音频信息"
            attachment_data = await msg.download_media(file=bytes)
            attachment_filename = get_filename_from_document(msg.audio) or f"audio_{msg.id}.mp3"
            
        elif msg.text:
            subject = "【Telegram】新文字信息"
            
    except Exception as e:
        print(f"下载媒体文件时出错: {e}")
        attachment_data = None
        attachment_filename = None

    # 4. 调用邮件发送函数
    await send_email(subject, body_text, attachment_data, attachment_filename)


async def main():
    print("Userbot 监听服务已启动...")
    print(f"正在监听以下群组: {TARGET_CHAT_IDS}")
    await client.run_until_disconnected()

if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
