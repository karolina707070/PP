from django.db import models
from django.contrib.auth.models import AbstractUser


class Role(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name="Название роли")

    def __str__(self):
        return self.name


class User(AbstractUser):
    ROLE_CHOICES = (
        (1, 'Клиент'),
        (2, 'Менеджер'),
        (3, 'Специалист'),
        (4, 'Администратор'),
    )
    phone = models.CharField(max_length=20, blank=True, verbose_name="Телефон")
    role = models.ForeignKey(Role, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Роль")


    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name="custom_user_set",
        related_query_name="custom_user",
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name="custom_user_set",
        related_query_name="custom_user",
    )

    def __str__(self):
        return self.username




class Direction(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name="Направление")

    def __str__(self):
        return self.name

class RequestStatus(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name="Статус")

    def __str__(self):
        return self.name

class Request(models.Model):
    title = models.CharField(max_length=200, verbose_name="Название проекта")
    goal = models.TextField(blank=True, verbose_name="Цель")
    expected_results = models.TextField(blank=True, verbose_name="Ожидаемые результаты")
    description = models.TextField(blank=True, verbose_name="Описание")
    deadline = models.DateField(null=True, blank=True, verbose_name="Желаемый срок")
    budget = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Бюджет")
    submission_date = models.DateTimeField(auto_now_add=True, verbose_name="Дата подачи")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='requests', verbose_name="Клиент")
    direction = models.ForeignKey(Direction, on_delete=models.PROTECT, verbose_name="Направление")
    status = models.ForeignKey(RequestStatus, on_delete=models.PROTECT, default=1, verbose_name="Текущий статус")
    responsible_specialist = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='specialist_requests', verbose_name="Назначенный специалист")

    def __str__(self):
        return f"{self.title} (ID: {self.id})"

class Comment(models.Model):
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name='comments', verbose_name="Заявка")
    author = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Автор")
    text = models.TextField(verbose_name="Текст комментария")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата")

class Assessment(models.Model):
    request = models.OneToOneField(Request, on_delete=models.CASCADE, related_name='assessment', verbose_name="Заявка")
    specialist = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Специалист")
    labor_hours = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="Трудозатраты (ч)")
    resources = models.TextField(blank=True, verbose_name="Необходимые ресурсы")
    conclusion = models.TextField(blank=True, verbose_name="Заключение")
    assessment_date = models.DateTimeField(auto_now_add=True, verbose_name="Дата оценки")

