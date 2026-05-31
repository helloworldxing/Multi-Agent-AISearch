from __future__ import annotations

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr


class EmailConfigError(RuntimeError):
    pass


def send_email(to: str, subject: str, content: str) -> dict:
    """通过 SSL SMTP 发送纯文本邮件。

    必需环境变量：SMTP_HOST、SMTP_USER、SMTP_PASS。
    可选：SMTP_PORT（默认 465）、SMTP_SENDER_NAME。
    """
    if not to:
        raise EmailConfigError("收件邮箱为空")

    try:
        host = os.environ["SMTP_HOST"]
        user = os.environ["SMTP_USER"]
        password = os.environ["SMTP_PASS"]
    except KeyError as e:
        raise EmailConfigError(f"缺少 SMTP 环境变量: {e.args[0]}") from e

    port = int(os.environ.get("SMTP_PORT", "465"))
    sender_name = os.environ.get("SMTP_SENDER_NAME", "AI 研究助手")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = formataddr((sender_name, user))
    msg["To"] = to
    msg.attach(MIMEText(content, "plain", "utf-8"))

    with smtplib.SMTP_SSL(host, port, timeout=30) as server:
        server.login(user, password)
        server.sendmail(user, [to], msg.as_string())

    return {"to": to, "subject": subject}
