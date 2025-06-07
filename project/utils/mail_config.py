import os

def get_smtp_config():
    return {
        'server': os.getenv('MAIL_SERVER', 'smtp.gmail.com'),
        'port': int(os.getenv('MAIL_PORT', 587)),
        'use_tls': os.getenv('MAIL_USE_TLS', 'true').lower() == 'true',
        'username': os.getenv('MAIL_USERNAME'),
        'password': os.getenv('MAIL_PASSWORD'),
        'default_sender': os.getenv('MAIL_DEFAULT_SENDER'),
    }
