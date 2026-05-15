import os
import csv
import io
import base64
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import logout, authenticate, login
from django.contrib import messages
from django.db import connection
from django.http import HttpResponse
from django.db.models import Q
from django.core.paginator import Paginator
import matplotlib.pyplot as plt
from .models import Request, Direction, RequestStatus, RequestHistory, Notification, User
from .forms import RequestCreateForm, CommentForm, AssessmentForm, AssignSpecialistForm, CustomUserCreationForm
import matplotlib
matplotlib.use('Agg')



def create_notification(user, title, message, request_obj=None):
    Notification.objects.create(
        user=user,
        request=request_obj,
        title=title,
        message=message
    )



def log_history(request_obj, user, action):
    RequestHistory.objects.create(request=request_obj, user=user, action=action)



def is_admin(user):
    return user.is_authenticated and user.role and user.role.name == 'Администратор'


def is_head_or_admin(user):
    if not user.is_authenticated:
        return False
    role_name = user.role.name if user.role else ''
    return role_name in ['Начальник отдела', 'Администратор']


def is_specialist_or_admin(user):
    if not user.is_authenticated:
        return False
    role_name = user.role.name if user.role else ''
    return role_name in ['Специалист', 'Администратор']



def guest_view(request):
    return render(request, 'guest.html')



def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Регистрация прошла успешно! Добро пожаловать.')
            return redirect('home')
        else:
            messages.error(request, 'Исправьте ошибки в форме.')
    else:
        form = CustomUserCreationForm()
    return render(request, 'register.html', {'form': form})



def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Неверный логин или пароль')
    return render(request, 'login.html')


@login_required
def home(request):
    return render(request, 'home.html', {'user': request.user})


def logout_view(request):
    logout(request)
    messages.info(request, 'Вы вышли из системы')
    return redirect('login')



@login_required
def create_request(request):
    if request.user.role and request.user.role.name != 'Клиент':
        messages.error(request, 'Только клиенты могут создавать заявки.')
        return redirect('request_list')

    if request.method == 'POST':
        form = RequestCreateForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                new_request = form.save(commit=False)
                new_request.user = request.user
                default_status = RequestStatus.objects.filter(name='Новая').first()
                if default_status:
                    new_request.status = default_status
                new_request.save()
                log_history(new_request, request.user, f'Создал(а) заявку "{new_request.title}"')

                heads_and_admins = User.objects.filter(role__name__in=['Начальник отдела', 'Администратор'])
                for user in heads_and_admins:
                    create_notification(
                        user,
                        '📋 Новая заявка',
                        f'Клиент {request.user.username} создал новую заявку "{new_request.title}"',
                        new_request
                    )

                messages.success(request, 'Заявка создана.')
                return redirect('request_detail', pk=new_request.id)
            except Exception as e:
                messages.error(request, f'Ошибка: {str(e)}')
        else:
            messages.error(request, 'Исправьте ошибки в форме.')
    else:
        form = RequestCreateForm()
    return render(request, 'create_request.html', {'form': form})



@login_required
def request_list(request):
    try:
        requests_list = Request.objects.filter(delete_date__isnull=True).order_by('-submission_date')

        if request.user.role and request.user.role.name == 'Клиент':
            requests_list = requests_list.filter(user=request.user)
        elif request.user.role and request.user.role.name == 'Специалист':
            requests_list = requests_list.filter(responsible_specialist=request.user)

        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        if start_date and end_date:
            requests_list = requests_list.filter(
                submission_date__date__gte=start_date,
                submission_date__date__lte=end_date
            )

        search_query = request.GET.get('search', '')
        direction_id = request.GET.get('direction_id', '')
        status_id = request.GET.get('status', '')
        sort_by = request.GET.get('sort', '-submission_date')

        if search_query:
            requests_list = requests_list.filter(
                Q(title__icontains=search_query) | Q(goal__icontains=search_query)
            )

        if direction_id and direction_id != 'all':
            requests_list = requests_list.filter(direction_id=direction_id)

        if status_id and status_id != 'all':
            requests_list = requests_list.filter(status_id=status_id)

        if sort_by == 'budget_asc':
            requests_list = requests_list.order_by('budget')
        elif sort_by == 'budget_desc':
            requests_list = requests_list.order_by('-budget')
        elif sort_by == 'deadline_asc':
            requests_list = requests_list.order_by('deadline')
        else:
            requests_list = requests_list.order_by('-submission_date')

        paginator = Paginator(requests_list, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        query_params = request.GET.copy()
        if 'page' in query_params:
            query_params.pop('page')
        query_string = query_params.urlencode()

        context = {
            'page_obj': page_obj,
            'directions': Direction.objects.all(),
            'statuses': RequestStatus.objects.all(),
            'search_query': search_query,
            'selected_direction': direction_id,
            'selected_status': status_id,
            'sort_by': sort_by,
            'query_string': query_string,
        }

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return render(request, 'partials/requests_table.html', context)

        return render(request, 'request_list.html', context)
    except Exception as e:
        messages.error(request, f'Ошибка загрузки списка: {str(e)}')
        return redirect('home')



@login_required
def request_detail(request, pk):
    try:
        req = get_object_or_404(Request, pk=pk, delete_date__isnull=True)
    except:
        messages.error(request, 'Заявка не найдена')
        return redirect('request_list')

    if request.user.role and request.user.role.name == 'Клиент' and req.user != request.user:
        messages.error(request, 'Нет доступа')
        return redirect('request_list')
    if request.user.role and request.user.role.name == 'Специалист' and req.responsible_specialist != request.user:
        messages.error(request, 'Вы можете просматривать только заявки, на которые вы назначены')
        return redirect('request_list')

    comments = req.comments.all().order_by('created_at')
    assessment = getattr(req, 'assessment', None)

    assign_form = None
    if is_head_or_admin(request.user):
        initial_data = {}
        if req.responsible_specialist:
            initial_data['specialist'] = req.responsible_specialist.id
        assign_form = AssignSpecialistForm(initial=initial_data)
        if request.method == 'POST' and 'assign_specialist' in request.POST:
            form = AssignSpecialistForm(request.POST)
            if form.is_valid():
                specialist = form.cleaned_data['specialist']
                old_specialist = req.responsible_specialist
                req.responsible_specialist = specialist
                req.save()
                if specialist:
                    log_history(req, request.user, f'Назначил(а) специалиста {specialist.username}')
                    create_notification(
                        specialist,
                        'Вам назначена заявка',
                        f'Вам назначена заявка "{req.title}" от клиента {req.user.username}',
                        req
                    )
                else:
                    log_history(req, request.user,
                                f'Снял(а) назначение специалиста {old_specialist.username if old_specialist else ""}')
                messages.success(request, f'Специалист {specialist.username if specialist else "снят"} назначен')
                return redirect('request_detail', pk=pk)

    if request.method == 'POST' and 'change_status' in request.POST and is_head_or_admin(request.user):
        new_status_id = request.POST.get('status_id')
        if new_status_id:
            try:
                new_status = RequestStatus.objects.get(id=new_status_id)
                old_status = req.status
                req.status = new_status
                req.save()
                log_history(req, request.user, f'Изменил(а) статус с "{old_status.name}" на "{new_status.name}"')
                create_notification(
                    req.user,
                    f'Статус заявки изменён',
                    f'Ваша заявка "{req.title}" теперь имеет статус "{new_status.name}"',
                    req
                )
                messages.success(request, f'Статус изменён на "{new_status.name}"')
            except RequestStatus.DoesNotExist:
                messages.error(request, 'Некорректный статус')
            return redirect('request_detail', pk=pk)

    if request.method == 'POST' and 'add_comment' in request.POST:
        form = CommentForm(request.POST)
        if form.is_valid():
            try:
                comment = form.save(commit=False)
                comment.request = req
                comment.author = request.user
                comment.save()
                log_history(req, request.user, f'Добавил(а) комментарий: "{comment.text[:50]}..."')
                messages.success(request, 'Комментарий добавлен')
            except Exception as e:
                messages.error(request, f'Ошибка: {str(e)}')
            return redirect('request_detail', pk=pk)

    if request.method == 'POST' and 'add_assessment' in request.POST and is_specialist_or_admin(request.user):
        if request.user.role and request.user.role.name == 'Специалист' and req.responsible_specialist != request.user:
            messages.error(request, 'Вы можете оценивать только заявки, на которые вы назначены')
            return redirect('request_detail', pk=pk)
        form = AssessmentForm(request.POST)
        if form.is_valid():
            try:
                assessment_obj = form.save(commit=False)
                assessment_obj.request = req
                assessment_obj.specialist = request.user
                assessment_obj.save()
                log_history(req, request.user, f'Выставил(а) оценку (трудозатраты: {assessment_obj.labor_hours} ч.)')
                messages.success(request, 'Оценка сохранена')
            except Exception as e:
                messages.error(request, f'Ошибка: {str(e)}')
            return redirect('request_detail', pk=pk)

    return render(request, 'request_detail.html', {
        'request_obj': req,
        'comments': comments,
        'assessment': assessment,
        'comment_form': CommentForm(),
        'assessment_form': AssessmentForm(),
        'assign_form': assign_form,
        'statuses': RequestStatus.objects.all(),
    })



@login_required
def request_edit(request, pk):
    try:
        req = get_object_or_404(Request, pk=pk, delete_date__isnull=True)
    except:
        messages.error(request, 'Заявка не найдена')
        return redirect('request_list')

    can_edit = False
    if request.user.role:
        role = request.user.role.name
        if role in ['Начальник отдела', 'Администратор']:
            can_edit = True
        elif role == 'Клиент' and req.user == request.user:
            new_status = RequestStatus.objects.filter(name='Новая').first()
            if new_status and req.status == new_status:
                can_edit = True

    if not can_edit:
        messages.error(request, 'Нет прав на редактирование')
        return redirect('request_detail', pk=pk)

    if request.method == 'POST':
        form = RequestCreateForm(request.POST, request.FILES, instance=req)
        if form.is_valid():
            try:
                old_image = req.image.path if req.image else None
                updated = form.save()
                changed_fields = form.changed_data
                if changed_fields:
                    log_history(req, request.user, f'Отредактировал(а) поля: {", ".join(changed_fields)}')
                if old_image and updated.image and old_image != updated.image.path and os.path.exists(old_image):
                    os.remove(old_image)
                messages.success(request, 'Заявка обновлена')
                return redirect('request_detail', pk=pk)
            except Exception as e:
                messages.error(request, f'Ошибка: {str(e)}')
        else:
            messages.error(request, 'Исправьте ошибки')
    else:
        form = RequestCreateForm(instance=req)
    return render(request, 'create_request.html', {'form': form, 'edit': True})



@login_required
def confirm_delete(request, pk):
    req = get_object_or_404(Request, pk=pk)

    if request.user.role and request.user.role.name == 'Администратор':
        pass
    elif request.user.role and request.user.role.name == 'Клиент' and req.user == request.user:
        pass
    else:
        messages.error(request, 'Нет прав на удаление')
        return redirect('request_list')

    if request.method == 'POST' and request.POST.get('confirm') == 'yes':
        try:
            if request.user.role and request.user.role.name == 'Администратор':
                if req.image and os.path.exists(req.image.path):
                    os.remove(req.image.path)
                log_history(req, request.user, 'ПОЛНОСТЬЮ УДАЛИЛ(А) заявку')
                req.delete()
                messages.success(request, 'Заявка полностью удалена')
            else:
                log_history(req, request.user, 'Поместил(а) в архив (мягкое удаление)')
                req.soft_delete()
                messages.success(request, 'Заявка перемещена в архив')
        except Exception as e:
            messages.error(request, f'Ошибка: {str(e)}')
        return redirect('request_list')
    return render(request, 'confirm_delete.html', {'request_obj': req})



@user_passes_test(is_admin)
def restore_request(request, pk):
    try:
        req = get_object_or_404(Request, pk=pk, delete_date__isnull=False)
        log_history(req, request.user, 'Восстановил(а) заявку из архива')
        req.restore()
        messages.success(request, 'Заявка восстановлена')
    except Exception as e:
        messages.error(request, f'Ошибка: {str(e)}')
    return redirect('deleted_requests')

@user_passes_test(is_admin)
def hard_delete(request, pk):

    try:
        req = get_object_or_404(Request, pk=pk)

        if req.image and os.path.exists(req.image.path):
            os.remove(req.image.path)

        log_history(req, request.user, f'ПОЛНОСТЬЮ УДАЛИЛ(А) заявку "{req.title}" из архива')
        req.delete()
        messages.success(request, f'Заявка "{req.title}" полностью удалена из системы')
    except Exception as e:
        messages.error(request, f'Ошибка при удалении: {str(e)}')
    return redirect('deleted_requests')


@user_passes_test(is_admin)
def deleted_requests(request):
    try:
        deleted = Request.objects.filter(delete_date__isnull=False).order_by('-delete_date')
        search = request.GET.get('search', '')
        if search:
            deleted = deleted.filter(title__icontains=search)
        sort = request.GET.get('sort', '-delete_date')
        if sort == 'title':
            deleted = deleted.order_by('title')
        else:
            deleted = deleted.order_by('-delete_date')
        return render(request, 'deleted_requests.html', {'requests': deleted})
    except Exception as e:
        messages.error(request, f'Ошибка загрузки архива: {str(e)}')
        return redirect('home')



@user_passes_test(is_head_or_admin)
def statistics(request):
    try:
        import matplotlib.pyplot as plt
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans']

        statuses = RequestStatus.objects.all()
        labels, counts = [], []
        colors = ['#3498db', '#f39c12', '#2ecc71', '#e74c3c', '#9b59b6']

        for st in statuses:
            cnt = Request.objects.filter(status=st, delete_date__isnull=True).count()
            if cnt > 0:
                labels.append(st.name)
                counts.append(cnt)

        if not counts:
            return render(request, 'statistics.html', {'graph': None})

        plt.figure(figsize=(10, 6))
        bars = plt.bar(labels, counts, color=colors[:len(labels)], edgecolor='black', linewidth=1)

        for bar, count in zip(bars, counts):
            plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1,
                     str(count), ha='center', va='bottom', fontsize=12, fontweight='bold')

        plt.title('Распределение заявок по статусам', fontsize=16, fontweight='bold', pad=20)
        plt.xlabel('Статус', fontsize=12, fontweight='bold')
        plt.ylabel('Количество заявок', fontsize=12, fontweight='bold')
        plt.xticks(rotation=0, fontsize=11)
        plt.yticks(fontsize=10)
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        graph_base64 = base64.b64encode(buf.read()).decode('utf-8')
        plt.close()

        return render(request, 'statistics.html', {'graph': graph_base64})
    except Exception as e:
        messages.error(request, f'Ошибка графика: {str(e)}')
        return redirect('home')



@user_passes_test(is_head_or_admin)
def requests_report(request):
    try:
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        report_data = None

        if start_date and end_date:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT d.name, COUNT(r.id), d.id
                    FROM cint_request r
                    JOIN cint_direction d ON r.direction_id = d.id
                    WHERE r.submission_date BETWEEN %s AND %s
                      AND r.delete_date IS NULL
                    GROUP BY d.name, d.id
                    ORDER BY d.name
                """, [start_date, end_date])
                report_data = cursor.fetchall()

        return render(request, 'report.html', {'report_data': report_data})
    except Exception as e:
        messages.error(request, f'Ошибка формирования отчёта: {e}')
        return render(request, 'report.html')



@login_required
def notifications_view(request):
    notifications = request.user.notifications.all()
    return render(request, 'notifications.html', {'notifications': notifications})


@login_required
def mark_notification_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save()
    return redirect('notifications')

@login_required
def delete_notification(request, pk):

    try:
        notification = get_object_or_404(Notification, pk=pk, user=request.user)
        notification.delete()
        messages.success(request, 'Уведомление удалено')
    except Exception as e:
        messages.error(request, f'Ошибка: {str(e)}')
    return redirect('notifications')


@login_required
def export_requests_csv(request):
    try:
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="requests.csv"'

        response.write('\uFEFF')
        writer = csv.writer(response)
        writer.writerow(['ID', 'Название', 'Клиент', 'Статус', 'Дата подачи'])

        for req in Request.objects.select_related('user', 'status').filter(delete_date__isnull=True):
            writer.writerow([req.id, req.title, req.user.username, req.status.name, req.submission_date])

        return response
    except Exception as e:
        messages.error(request, f'Ошибка экспорта: {e}')
        return redirect('request_list')