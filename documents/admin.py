from django.contrib import admin
from django.contrib import messages
from .models import Document
from documents.tasks import send_status_notification, send_telegram_notification
from django.urls import reverse


@admin.action(description="✅ Подтвердить выбранные документы")
def approve_documents(modeladmin, request, queryset):
    print("=== ACTION: approve_documents ===")
    updated = queryset.filter(status__in=["pending", "rejected"]).update(
        status="approved"
    )
    for doc in queryset.filter(status="approved"):
        doc_url = request.build_absolute_uri(
            reverse("documents:document-detail", kwargs={"pk": doc.id})
        )

        send_status_notification.delay(
            user_email=doc.author.email,
            doc_title=doc.title,
            status="подтверждён",
            doc_url=doc_url,
        )

        if doc.author.telegram_notifications is True:
            print("=== У пользователя включена рассылка ===")
            send_telegram_notification.delay(
                chat_id=doc.author.telegram_chat_id,
                message_lines=[
                    f'✅ Ваш документ "{doc.title}" был подтверждён.',
                    f"[Открыть документ]({doc_url})",
                ],
            )

    modeladmin.message_user(
        request, f"Подтверждено документов: {updated}", level=messages.SUCCESS
    )


@admin.action(description="❌ Отклонить выбранные документы")
def reject_documents(modeladmin, request, queryset):
    print("=== ACTION: reject_documents ===")
    updated = queryset.filter(status__in=["pending", "approved"]).update(
        status="rejected"
    )
    for doc in queryset.filter(status="rejected"):
        doc_url = request.build_absolute_uri(
            reverse("documents:document-detail", kwargs={"pk": doc.id})
        )

        send_status_notification.delay(
            user_email=doc.author.email,
            doc_title=doc.title,
            status="отклонён",
            doc_url=doc_url,
        )

        if doc.author.telegram_notifications is True:
            print("=== У пользователя включена рассылка ===")
            send_telegram_notification.delay(
                chat_id=doc.author.telegram_chat_id,
                message_lines=[
                    f'❌ Ваш документ "{doc.title}" был отклонён.',
                    f"[Открыть документ]({doc_url})",
                ],
            )

    modeladmin.message_user(
        request, f"Отклонено документов: {updated}", level=messages.SUCCESS
    )


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ["title", "author", "status", "uploaded_at"]
    list_filter = ["status", "author"]
    search_fields = ["title", "author__username"]
    actions = [approve_documents, reject_documents]
    readonly_fields = ["uploaded_at"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("author")
