from flask_mail import Message
from api.app import mail
from api.app import celery


@celery.task(bind=True)
def send_mail(self, from_address: str, to_address: str, subject: str, html: str, text: str):
    msg = Message(subject, sender=from_address, recipients=[to_address])
    msg.html = html
    msg.body = text
    mail.send(msg)
