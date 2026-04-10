from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import Request, Direction, RequestStatus, Role
from .forms import RequestCreateForm

User = get_user_model()


class RequestModuleTests(TestCase):

    def setUp(self):
        self.client_role = Role.objects.create(name='Клиент')
        self.manager_role = Role.objects.create(name='Менеджер')
        self.specialist_role = Role.objects.create(name='Специалист')
        self.admin_role = Role.objects.create(name='Администратор')


        self.client = User.objects.create_user(username='client', password='123', role=self.client_role)
        self.manager = User.objects.create_user(username='manager', password='123', role=self.manager_role)
        self.specialist = User.objects.create_user(username='spec', password='123', role=self.specialist_role)


        self.direction = Direction.objects.create(name='Веб-разработка')
        self.status_new = RequestStatus.objects.create(name='Новая')
        self.status_approved = RequestStatus.objects.create(name='Одобрена')


        self.request = Request.objects.create(
            title='Тестовая заявка',
            goal='Цель',
            expected_results='Результаты',
            description='Описание',
            user=self.client,
            direction=self.direction,
            status=self.status_new
        )


        self.client_http = Client()


    def test_soft_delete_and_restore(self):
        self.request.soft_delete()
        self.assertIsNotNone(self.request.delete_date)

        active_requests = Request.objects.filter(delete_date__isnull=True)
        self.assertNotIn(self.request, active_requests)


        self.request.restore()
        self.assertIsNone(self.request.delete_date)
        active_requests = Request.objects.filter(delete_date__isnull=True)
        self.assertIn(self.request, active_requests)


    def test_budget_validation(self):
        form_data = {
            'title': 'Тест', 'goal': 'Цель', 'expected_results': 'Результаты',
            'description': 'Описание', 'direction': self.direction.id, 'budget': -100
        }
        form = RequestCreateForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('budget', form.errors)
        self.assertEqual(form.errors['budget'][0], 'Бюджет должен быть положительным числом.')

        form_data['budget'] = 50000
        form = RequestCreateForm(data=form_data)
        self.assertNotIn('budget', form.errors)

    def test_search_filter(self):
        Request.objects.create(
            title='Другая заявка', goal='...', expected_results='...', description='...',
            user=self.client, direction=self.direction, status=self.status_new
        )
        self.client_http.login(username='client', password='123')
        response = self.client_http.get(reverse('request_list'), {'search': 'Тестовая'})
        self.assertEqual(response.status_code, 200)
        page_obj = response.context['page_obj']
        self.assertEqual(page_obj.paginator.count, 1)
        self.assertEqual(page_obj[0].title, 'Тестовая заявка')

    def test_client_can_see_only_own_requests(self):
        other_client = User.objects.create_user(username='other', password='123', role=self.client_role)
        Request.objects.create(
            title='Чужая заявка', goal='...', expected_results='...', description='...',
            user=other_client, direction=self.direction, status=self.status_new
        )
        self.client_http.login(username='client', password='123')
        response = self.client_http.get(reverse('request_list'))
        page_obj = response.context['page_obj']
        self.assertEqual(page_obj.paginator.count, 1)
        self.assertEqual(page_obj[0].title, 'Тестовая заявка')

    def test_specialist_sees_only_assigned_requests(self):
        self.request.responsible_specialist = self.specialist
        self.request.save()
        Request.objects.create(
            title='Без специалиста', goal='...', expected_results='...', description='...',
            user=self.client, direction=self.direction, status=self.status_new
        )
        self.client_http.login(username='spec', password='123')
        response = self.client_http.get(reverse('request_list'))
        page_obj = response.context['page_obj']
        self.assertEqual(page_obj.paginator.count, 1)
        self.assertEqual(page_obj[0].title, 'Тестовая заявка')