from jinja2 import Environment, FileSystemLoader, select_autoescape
from email.message import EmailMessage
from datetime import datetime
import os, smtplib


import rq
from redis.asyncio import Redis

redis_conn = Redis.from_url(os.getenv("REDIS_URL"))
email_queue = rq.Queue("email", connection=redis_conn)


API_TITLE = os.getenv("API_TITLE")

SMTP_HOST = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT"))
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_REPLY_TO = os.getenv("EMAIL_REPLY_TO")

async def send_email(to_email: str, subject: str, body: str, subtype: str = "plain", from_purpose: str = "General"):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{API_TITLE} {from_purpose} <{EMAIL_SENDER}>"
    msg["Reply-To"] = EMAIL_REPLY_TO
    msg["To"] = to_email
    msg.set_content(body, subtype=subtype)
    
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)

async def render_email_template(template_name: str, context: dict) -> str:
    templates_dir = os.path.join(os.path.dirname(__file__), "../templates/email")
    env = Environment(
        loader=FileSystemLoader(templates_dir),
        autoescape=select_autoescape(['html', 'xml'])
    )
    env.globals['now'] = datetime.now
    env.globals['API_TITLE'] = API_TITLE
    template = env.get_template(template_name)
    return template.render(context)