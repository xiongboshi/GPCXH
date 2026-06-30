import smtplib
from email.mime.text import MIMEText
from email.header import Header
from typing import List

def send_email_notification(
    to_emails: List[str],
    subject: str,
    body: str,
    smtp_server: str = "smtp.qq.com",      # 例如 QQ 邮箱
    smtp_port: int = 465,                  # SSL 端口
    sender_email: str = "your_email@qq.com",
    sender_password: str = "your_auth_code"  # 注意：是授权码，不是登录密码！
):
    """
    发送邮件通知（支持 SSL）
    
    参数说明：
    - to_emails: 收件人列表，如 ["user1@example.com", "user2@example.com"]
    - subject: 邮件主题
    - body: 邮件正文（纯文本）
    - smtp_server: SMTP 服务器地址（QQ: smtp.qq.com, 163: smtp.163.com, Gmail: smtp.gmail.com）
    - smtp_port: 通常 465 (SSL) 或 587 (TLS)
    - sender_email: 发件人邮箱
    - sender_password: 邮箱 SMTP 授权码（非登录密码！）
    """
    try:
        # 创建 MIMEText 对象
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['From'] = Header(sender_email)
        msg['To'] = Header(", ".join(to_emails))
        msg['Subject'] = Header(subject, 'utf-8')

        # 连接 SMTP 服务器（SSL）
        server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_emails, msg.as_string())
        server.quit()
        print(f"✅ 邮件已成功发送至: {', '.join(to_emails)}")
        return True
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")
        return False