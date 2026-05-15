from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import Request, Direction, RequestStatus, Role
from .forms import RequestCreateForm

User = get_user_model()


class RequestModuleTests(TestCase):
    def setUp(self):

        self.client_role = Role.objects.create(name='Клиент')
        self.specialist_role = Role.objects.create(name='Специалист')
        self.direction = Direction.objects.create(name='Веб-разработка')
        self.status_new = RequestStatus.objects.create(name='Новая')
        self.user = User.objects.create_user(username='client', password='123', role=self.client_role)


    def test_soft_delete_and_restore(self):
        request = Request.objects.create(
            title='Тест',
            user=self.user,
            direction=self.direction,
            status=self.status_new
        )
        request.soft_delete()
        self.assertIsNotNone(request.delete_date)
        active_requests = Request.objects.filter(delete_date__isnull=True)
        self.assertNotIn(request, active_requests)
        request.restore()
        self.assertIsNone(request.delete_date)
        active_requests = Request.objects.filter(delete_date__isnull=True)
        self.assertIn(request, active_requests)


    def test_budget_validation(self):
        form_data = {
            'title': 'Тест',
            'goal': 'Цель',
            'expected_results': 'Результаты',
            'description': 'Описание',
            'direction': self.direction.id,
            'budget': -100
        }
        form = RequestCreateForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('budget', form.errors)
        self.assertEqual(form.errors['budget'][0], 'Бюджет должен быть положительным числом.')


    def test_search_filter(self):
        Request.objects.create(
            title='Тестовая заявка',
            user=self.user,
            direction=self.direction,
            status=self.status_new
        )
        Request.objects.create(
            title='Другая',
            user=self.user,
            direction=self.direction,
            status=self.status_new
        )
        self.client.login(username='client', password='123')
        response = self.client.get(reverse('request_list'), {'search': 'Тестовая'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page_obj'].paginator.count, 1)
        self.assertEqual(response.context['page_obj'][0].title, 'Тестовая заявка')


    def test_client_sees_only_own_requests(self):
        other_user = User.objects.create_user(username='other', password='123', role=self.client_role)
        Request.objects.create(
            title='Своя',
            user=self.user,
            direction=self.direction,
            status=self.status_new
        )
        Request.objects.create(
            title='Чужая',
            user=other_user,
            direction=self.direction,
            status=self.status_new
        )
        self.client.login(username='client', password='123')
        response = self.client.get(reverse('request_list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page_obj'].paginator.count, 1)
        self.assertEqual(response.context['page_obj'][0].title, 'Своя')


    def test_specialist_sees_only_assigned_requests(self):
        specialist = User.objects.create_user(username='spec', password='123', role=self.specialist_role)
        request = Request.objects.create(
            title='Назначенная',
            user=self.user,
            direction=self.direction,
            status=self.status_new
        )
        request.responsible_specialist = specialist
        request.save()
        Request.objects.create(
            title='Не назначенная',
            user=self.user,
            direction=self.direction,
            status=self.status_new
        )
        self.client.login(username='spec', password='123')
        response = self.client.get(reverse('request_list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page_obj'].paginator.count, 1)
        self.assertEqual(response.context['page_obj'][0].title, 'Назначенная')