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
from django.db.models import Count, Sum, Avg, Q
from django.db.models.functions import TruncMonth



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
        status_name = request.GET.get('status', '')
        sort_by = request.GET.get('sort', '-submission_date')

        if search_query:
            requests_list = requests_list.filter(
                Q(title__icontains=search_query) | Q(goal__icontains=search_query)
            )

        if direction_id and direction_id != 'all':
            requests_list = requests_list.filter(direction_id=direction_id)

        if status_name and status_name != 'all':
            requests_list = requests_list.filter(status__name=status_name)

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
            'selected_status': status_name,
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

    # Назначение исполнителя (только админ и начальник отдела)
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
                    log_history(req, request.user, f'Назначил(а) исполнителя {specialist.username}')
                    create_notification(
                        specialist,
                        'Вам назначена заявка',
                        f'Вы назначены исполнителем по заявке "{req.title}" от клиента {req.user.username}',
                        req
                    )
                else:
                    log_history(req, request.user,
                                f'Снял(а) исполнителя {old_specialist.username if old_specialist else ""}')
                messages.success(request, f'Исполнитель {specialist.username if specialist else "снят"} назначен')
                return redirect('request_detail', pk=pk)

    # Изменение статуса — ТОЛЬКО СПЕЦИАЛИСТ и АДМИН
    if request.method == 'POST' and 'change_status' in request.POST:
        if not (request.user.role and request.user.role.name in ['Специалист', 'Администратор']):
            messages.error(request, 'Нет прав на изменение статуса')
            return redirect('request_detail', pk=pk)

        if request.user.role.name == 'Специалист' and req.responsible_specialist != request.user:
            messages.error(request, 'Вы можете менять статус только в назначенных вам заявках')
            return redirect('request_detail', pk=pk)

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
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans']

        base_qs = Request.objects.filter(delete_date__isnull=True)

        # Карточки
        total_requests = base_qs.count()
        new_count = base_qs.filter(status__name='Новая').count()
        approved_count = base_qs.filter(status__name='Одобрена').count()
        rejected_count = base_qs.filter(status__name='Отклонена').count()
        approval_rate = round(approved_count / total_requests * 100, 1) if total_requests > 0 else 0
        avg_budget = base_qs.filter(status__name='Одобрена', budget__isnull=False).aggregate(avg=Avg('budget'))['avg'] or 0

        # График 1: пирог
        pie_chart = None
        if total_requests > 0:
            labels, counts, colors = [], [], ['#3498db', '#2ecc71', '#e74c3c']
            for name, color in zip(['Новая', 'Одобрена', 'Отклонена'], colors):
                cnt = base_qs.filter(status__name=name).count()
                if cnt > 0:
                    labels.append(name)
                    counts.append(cnt)
            if counts:
                fig, ax = plt.subplots(figsize=(7, 7))
                ax.pie(counts, labels=labels, autopct='%1.1f%%', startangle=90,
                       colors=colors[:len(labels)], wedgeprops={'edgecolor': 'white', 'linewidth': 2})
                ax.set_title('Распределение заявок по статусам', fontsize=14, fontweight='bold')
                buf = io.BytesIO()
                plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
                buf.seek(0)
                pie_chart = base64.b64encode(buf.read()).decode('utf-8')
                plt.close()

        # График 2: столбцы по направлениям
        bar_chart = None
        direction_data = base_qs.values('direction__name').annotate(
            total=Count('id'),
            new=Count('id', filter=Q(status__name='Новая')),
            approved=Count('id', filter=Q(status__name='Одобрена')),
            rejected=Count('id', filter=Q(status__name='Отклонена')),
        ).order_by('-total')[:8]
        if direction_data:
            directions = [d['direction__name'] for d in direction_data]
            x = range(len(directions))
            width = 0.25
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.bar([i - width for i in x], [d['new'] for d in direction_data], width, label='Новые', color='#3498db')
            ax.bar(x, [d['approved'] for d in direction_data], width, label='Одобрены', color='#2ecc71')
            ax.bar([i + width for i in x], [d['rejected'] for d in direction_data], width, label='Отклонены', color='#e74c3c')
            ax.set_xticks(x)
            ax.set_xticklabels(directions, rotation=30, ha='right')
            ax.legend()
            ax.yaxis.grid(True, linestyle='--', alpha=0.3)
            plt.tight_layout()
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
            buf.seek(0)
            bar_chart = base64.b64encode(buf.read()).decode('utf-8')
            plt.close()

        # График 3: линия по месяцам
        line_chart = None
        monthly_data = base_qs.annotate(month=TruncMonth('submission_date')).values('month').annotate(
            total=Count('id'),
            approved=Count('id', filter=Q(status__name='Одобрена'))
        ).order_by('month')[:12]
        if monthly_data:
            months = [d['month'].strftime('%b %Y') if d['month'] else '?' for d in monthly_data]
            fig, ax = plt.subplots(figsize=(12, 5))
            ax.plot(range(len(months)), [d['total'] for d in monthly_data], 'o-', color='#3498db', linewidth=2.5, label='Всего')
            ax.plot(range(len(months)), [d['approved'] for d in monthly_data], 's--', color='#2ecc71', linewidth=2, label='Одобрено')
            ax.set_xticks(range(len(months)))
            ax.set_xticklabels(months, rotation=30, ha='right')
            ax.legend()
            ax.yaxis.grid(True, linestyle='--', alpha=0.3)
            plt.tight_layout()
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
            buf.seek(0)
            line_chart = base64.b64encode(buf.read()).decode('utf-8')
            plt.close()

        # Топ клиентов
        top_clients = base_qs.values('user__username', 'user__first_name', 'user__last_name').annotate(
            total=Count('id'),
            approved=Count('id', filter=Q(status__name='Одобрена')),
        ).order_by('-total')[:5]

        # Таблица направлений
        direction_table = base_qs.values('direction__name').annotate(
            total=Count('id'),
            new=Count('id', filter=Q(status__name='Новая')),
            approved=Count('id', filter=Q(status__name='Одобрена')),
            rejected=Count('id', filter=Q(status__name='Отклонена')),
        ).order_by('-total')

        context = {
            'total_requests': total_requests,
            'new_count': new_count,
            'approved_count': approved_count,
            'rejected_count': rejected_count,
            'approval_rate': approval_rate,
            'avg_budget': avg_budget,
            'pie_chart': pie_chart,
            'bar_chart': bar_chart,
            'line_chart': line_chart,
            'top_clients': top_clients,
            'direction_table': direction_table,
        }
        return render(request, 'statistics.html', context)
    except Exception as e:
        messages.error(request, f'Ошибка построения статистики: {str(e)}')
        return redirect('home')



@user_passes_test(is_head_or_admin)
def requests_report(request):
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    direction_id = request.GET.get('direction_id', 'all')
    status_name = request.GET.get('status', 'all')
    report_type = request.GET.get('report_type', 'summary')

    report_data = None
    summary = None
    detailed_list = None
    specialist_data = None

    if start_date and end_date:
        qs = Request.objects.filter(
            submission_date__date__gte=start_date,
            submission_date__date__lte=end_date,
            delete_date__isnull=True
        ).select_related('user', 'status', 'direction')

        if direction_id != 'all':
            qs = qs.filter(direction_id=direction_id)
        if status_name != 'all':
            qs = qs.filter(status__name=status_name)

        summary = {
            'total': qs.count(),
            'new': qs.filter(status__name='Новая').count(),
            'approved': qs.filter(status__name='Одобрена').count(),
            'rejected': qs.filter(status__name='Отклонена').count(),
            'total_budget': qs.filter(budget__isnull=False).aggregate(s=Sum('budget'))['s'] or 0,
            'avg_budget': qs.filter(budget__isnull=False).aggregate(a=Avg('budget'))['a'] or 0,
            'period_start': start_date,
            'period_end': end_date,
        }

        if report_type == 'summary':
            report_data = qs.values('direction__name').annotate(
                total=Count('id'),
                new=Count('id', filter=Q(status__name='Новая')),
                approved=Count('id', filter=Q(status__name='Одобрена')),
                rejected=Count('id', filter=Q(status__name='Отклонена')),
                total_budget=Sum('budget', filter=Q(budget__isnull=False)),
            ).order_by('-total')
        elif report_type == 'detailed':
            detailed_list = qs.order_by('-submission_date')[:200]
        elif report_type == 'specialist':
            specialist_data = qs.filter(responsible_specialist__isnull=False).values('responsible_specialist__username').annotate(
                total=Count('id'),
                approved=Count('id', filter=Q(status__name='Одобрена')),
                rejected=Count('id', filter=Q(status__name='Отклонена')),
                avg_hours=Avg('assessment__labor_hours'),
            ).order_by('-total')

    directions = Direction.objects.all()
    statuses = RequestStatus.objects.all()

    context = {
        'directions': directions,
        'statuses': statuses,
        'report_data': report_data,
        'summary': summary,
        'detailed_list': detailed_list,
        'specialist_data': specialist_data,
        'start_date': start_date,
        'end_date': end_date,
        'selected_direction': direction_id,
        'selected_status': status_name,
        'report_type': report_type,
    }
    return render(request, 'report.html', context)



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


@login_required
def print_request(request, pk):
    req = get_object_or_404(Request, pk=pk, delete_date__isnull=True)
    assessment = getattr(req, 'assessment', None)
    return render(request, 'print_request.html', {'req': req, 'assessment': assessment})