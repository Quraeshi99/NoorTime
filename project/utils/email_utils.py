# project/utils/email_utils.py

import smtplib
from email.mime.text import MIMEText
from flask import current_app
from .mail_config import get_smtp_config

def send_otp_email(to_email, otp_code):
    smtp_config = get_smtp_config()  # ⬅️ Dynamic config fetch

    subject = "तुम्हारा OTP कोड"
    body = f"Your OTP code is: {otp_code}\nThis code is valid for 10 minutes."

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = smtp_config['default_sender']
    msg['To'] = to_email

    try:
        if smtp_config['use_tls']:
            with smtplib.SMTP(smtp_config['server'], smtp_config['port']) as server:
                server.starttls()
                server.login(smtp_config['username'], smtp_config['password'])
                server.send_message(msg)
        else:
            with smtplib.SMTP_SSL(smtp_config['server'], smtp_config['port']) as server:
                server.login(smtp_config['username'], smtp_config['password'])
                server.send_message(msg)

        current_app.logger.info(f"OTP sent to {to_email}")

    except Exception as e:
        current_app.logger.error(f"Failed to send OTP to {to_email}: {e}")
