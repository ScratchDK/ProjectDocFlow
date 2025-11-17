from django.contrib.auth.models import AbstractUser, PermissionsMixin, BaseUserManager
from django.db import models


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email обязателен")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser, PermissionsMixin):
    CITY_CHOICES = [
        ("Pyatigorsk", "Пятигорск"),
        ("Moscow", "Москва"),
        ("Saint Petersburg", "Санкт-Петербург"),
        ("Omsk", "Омск"),
    ]

    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    avatar = models.ImageField(upload_to="users/images/", blank=True, null=True)
    city = models.CharField(
        max_length=255,
        choices=CITY_CHOICES,
        null=True,
        blank=True,
        verbose_name="Город",
    )
    # Токен для потверждения почты при регестрации и для восстановления пароля
    confirmation_token = models.CharField(max_length=32, blank=True, null=True)
    telegram_notifications = models.BooleanField(
        default=False, verbose_name="Уведомления в Телеграм"
    )
    telegram_chat_id = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="Телеграм chat-id",
        help_text="Укажите телеграм chat-id",
    )

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email
