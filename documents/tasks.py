from celery import shared_task
from django.core.mail import send_mail
from telegram import Bot, ParseMode
from django.conf import settings


@shared_task
def send_status_notification(user_email, doc_title, status, doc_url):
    subject = f"Статус документа: {doc_title}"
    message = (
        f'Ваш документ "{doc_title}" был {status}.\n' f"Проверьте в системе: {doc_url}"
    )
    send_mail(
        subject,
        message,
        from_email=None,
        recipient_list=[user_email],
        fail_silently=False,
    )


@shared_task(bind=True, max_retries=3)
def send_telegram_notification(self, chat_id, message_lines):
    try:
        print(f"[Telegram] Попытка отправить сообщение для chat_id={chat_id}")  # Логируем
        bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        bot.send_message(
            chat_id=chat_id,
            text="\n".join(message_lines),
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as e:
        print(f"[Telegram] ОШИБКА: {str(e)}")  # Вывод ошибки
        raise self.retry(exc=e)  # Повторная попытка
