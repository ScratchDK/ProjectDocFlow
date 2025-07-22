from django.core.management.base import BaseCommand
from users.models import CustomUser
from django.core.management import call_command


class Command(BaseCommand):
    help = "Добавляет троих пользователей с разными правами, пароль у всех пользователей (12345)"

    def handle(self, *args, **kwargs):
        self.stdout.write("Очистка существующих данных...")

        # Удаляем всех пользователей, кроме суперпользователей
        CustomUser.objects.filter(is_superuser=False).delete()

        self.stdout.write(self.style.SUCCESS("Старые данные успешно удалены!"))

        call_command("loaddata", "users_fixture.json")
        self.stdout.write(self.style.SUCCESS("Данные успешно загружены!"))
