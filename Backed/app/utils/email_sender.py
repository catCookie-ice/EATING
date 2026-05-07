"""邮件发送工具"""
import smtplib
from email.mime.text import MIMEText
from app.config import settings


def send_email(to_email: str, subject: str, body: str) -> bool:
    """发送邮件

    Args:
        to_email: 收件人邮箱
        subject: 邮件主题
        body: 邮件正文（HTML格式）

    Returns:
        是否发送成功
    """
    msg = MIMEText(body, 'html')
    msg['Subject'] = subject
    msg['From'] = settings.SMTP_USER
    msg['To'] = to_email

    try:
        server = smtplib.SMTP_SSL(settings.SMTP_SERVER, settings.SMTP_PORT)
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.SMTP_USER, [to_email], msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"邮件发送失败: {e}")
        return False
