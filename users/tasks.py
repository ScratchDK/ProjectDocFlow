from datetime import timedelta
from celery import shared_task
from django.utils import timezone
from users.models import CustomUser

# Нужен для создания сложных запросов к бд
from django.db.models import Q

from django.core.mail import send_mail
import config.settings as settings


@shared_task
def check_last_login():
    """Деактивирует пользователей, которые не заходили более 1 месяца."""
    now = timezone.now()

    one_month_ago = now - timedelta(days=30)

    inactive_users = CustomUser.objects.filter(is_active=True).filter(
        Q(last_login__lt=one_month_ago) | Q(last_login__isnull=True)
    )

    subject = "Деактивация неактивных пользователей!"
    message = f"Данные пользователи были деактивированы: {[user.email for user in inactive_users]}"

    from_email = settings.EMAIL_HOST_USER

    send_mail(
        subject,
        message,
        from_email,
        [from_email],
        fail_silently=False,
    )

    # Массовое обновление (одним запросом к БД)
    count_updated = inactive_users.update(is_active=False)

    return count_updated
