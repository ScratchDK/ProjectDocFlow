from django.core.mail import send_mail
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings

from config.settings import EMAIL_HOST_USER
from .models import Document

from django.http import HttpRequest
from django.urls import reverse

from documents.tasks import send_telegram_notification


@receiver(post_save, sender=Document)
def notify_admin_on_upload(sender, instance, created, **kwargs):
    if created:  # Письмо отправляется только при создании документа
        request = HttpRequest()

        request.META = {
            "SERVER_NAME": settings.DOMAIN_NAME,
            "SERVER_PORT": 80 if not settings.DEBUG else 8000,
            "wsgi.url_scheme": "https" if not settings.DEBUG else "http",
        }

        admin_url = request.build_absolute_uri(reverse("admin:documents_document_changelist"))

        subject = f"Новый документ загружен: {instance.title}"
        message = (
            f"Пользователь {instance.author.email} загрузил документ.\n"
            f"Тип: {instance.get_document_type_display()}\n"
            f"Ссылка в админку: {admin_url}"
        )
        send_mail(
            subject,
            message,
            from_email=None,  # Используется DEFAULT_FROM_EMAIL
            recipient_list=[EMAIL_HOST_USER],  # Получатель — админ
            fail_silently=False,
        )

        # Telegram-уведомление всем админам с chat_id
        admins = instance.author.__class__.objects.filter(
            is_staff=True,
            telegram_chat_id__isnull=False,
            telegram_notifications=True,
        )

        if not admins.exists():
            return

        message_lines = [
            "📄 Новый документ загружен",
            f"Автор: {instance.author.email}",
            f"Тип: {instance.get_document_type_display()}",
            f"Название: {instance.title}",
            f"Ссылка в админку: {admin_url}",
        ]

        for admin in admins:
            print(admin.telegram_chat_id)
            send_telegram_notification.delay(admin.telegram_chat_id, message_lines)
