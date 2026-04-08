from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from PIL import Image


class Role(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name="Название роли")

    def __str__(self):
        return self.name


class User(AbstractUser):
    phone = models.CharField(max_length=20, blank=True, verbose_name="Телефон")
    role = models.ForeignKey(Role, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Роль")
    groups = models.ManyToManyField('auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name="custom_user_set",
        related_query_name="custom_user",)

    user_permissions = models.ManyToManyField('auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name="custom_user_set",
        related_query_name="custom_user",)

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
    responsible_specialist = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                               related_name='specialist_requests',
                                               verbose_name="Назначенный специалист")

    image = models.ImageField(upload_to='request_images/', null=True, blank=True, verbose_name="Изображение")
    delete_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата удаления")

    def soft_delete(self):
        self.delete_date = timezone.now()
        self.save()

    def restore(self):
        self.delete_date = None
        self.save()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.image:
            self.resize_image()

    def resize_image(self):
        img_path = self.image.path
        img = Image.open(img_path)
        if img.width > 300 or img.height > 200:
            img.thumbnail((300, 200))
            img.save(img_path)

    def __str__(self):
        return f"{self.title} (ID: {self.id})"


class Comment(models.Model):
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class Assessment(models.Model):
    request = models.OneToOneField(Request, on_delete=models.CASCADE, related_name='assessment')
    specialist = models.ForeignKey(User, on_delete=models.CASCADE)
    labor_hours = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    resources = models.TextField(blank=True)
    conclusion = models.TextField(blank=True)
    assessment_date = models.DateTimeField(auto_now_add=True)