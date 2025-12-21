from django.db.models.signals import post_save
from django.dispatch import receiver 
from django.conf import settings
from django.core.mail import send_mail 
from django.contrib.auth.models import User
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=User)
def register_user(sender, instance, created, **kwargs):
    if created:
        # email credentials
        subject = "Email Verification"
        message = f"""
        Hi {instance.username}, welcome to our website!
        You are registered successfully. Now you are a member of our website.
        We hope you enjoy our service!
        """
        sender = settings.EMAIL_HOST_USER
        receiver = [instance.email]

        try:
            # send email
            send_mail(
                subject,
                message,
                sender,
                receiver,
                fail_silently=False,
            )
            logger.info(f"Email sent to {instance.email}")
        except Exception as e:
            logger.error(f"Failed to send email to {instance.email}: {e}")