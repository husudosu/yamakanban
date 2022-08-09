import threading

from flask import copy_current_request_context
from flask_mail import Message
from .app import mail


def send_async_email(subject, sender, recipients, text_body, html_body):
    """Sends an email async way.
    We don't need a distributed task queue for this simple task.

    Args:
        subject (str): Subject
        sender (str): Sender address
        recipients (List[str]): Recipients as array
        text_body (str): Body as text
        html_body (str): Body as HTML
    """
    message = Message(
        subject=subject,
        sender=sender,
        recipients=recipients,
        body=text_body,
        html=html_body
    )

    @copy_current_request_context
    def send_message(message):
        mail.send(message)

    sender = threading.Thread(
        name='mail_sender', target=send_message, args=(message,))
    sender.start()
