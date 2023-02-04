from flask_mail import Message
from api.app import mail
from api.app import celery


@celery.task(bind=True)
def send_mail(self, from_address, to_address, subject, html):
    print("Celery JOB running")
    msg = Message(subject, sender=from_address, recipients=[to_address])
    msg.html = html
    mail.send(msg)
