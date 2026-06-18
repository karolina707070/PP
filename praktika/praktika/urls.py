"""
URL configuration for praktika project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from cint import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('guest/', views.guest_view, name='guest'),
    path('logout/', views.logout_view, name='logout'),
    path('home/', views.home, name='home'),
    path('create/', views.create_request, name='create_request'),
    path('list/', views.request_list, name='request_list'),
    path('request/<int:pk>/', views.request_detail, name='request_detail'),
    path('request/<int:pk>/edit/', views.request_edit, name='request_edit'),
    path('confirm_delete/<int:pk>/', views.confirm_delete, name='confirm_delete'),
    path('deleted/', views.deleted_requests, name='deleted_requests'),
    path('restore/<int:pk>/', views.restore_request, name='restore'),
    path('statistics/', views.statistics, name='statistics'),
    path('report/', views.requests_report, name='requests_report'),
    path('export/csv/', views.export_requests_csv, name='export_csv'),
    path('notifications/', views.notifications_view, name='notifications'),
    path('notifications/read/<int:pk>/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/delete/<int:pk>/', views.delete_notification, name='delete_notification'),
    path('hard_delete/<int:pk>/', views.hard_delete, name='hard_delete'),
    path('request/<int:pk>/print/', views.print_request, name='print_request'),
]