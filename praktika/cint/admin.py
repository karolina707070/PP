from django.contrib import admin
from .models import User, Role, Direction, RequestStatus, Request, Comment, Assessment

@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'status', 'submission_date', 'responsible_specialist')
    list_filter = ('status', 'direction', 'submission_date')
    search_fields = ('title', 'description', 'user__username')

admin.site.register(User)
admin.site.register(Role)
admin.site.register(Direction)
admin.site.register(RequestStatus)
admin.site.register(Comment)
admin.site.register(Assessment)
