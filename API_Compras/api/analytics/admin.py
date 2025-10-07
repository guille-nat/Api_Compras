from django.contrib import admin
from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    """Administración de reportes en el panel de Django Admin."""

    list_display = [
        'id',
        'user',
        'report_type',
        'status',
        'created_at',
        'completed_at',
        'has_file'
    ]

    list_filter = [
        'report_type',
        'status',
        'created_at',
        'completed_at'
    ]

    search_fields = [
        'task_id',
        'user__username',
        'user__email',
        'error_message'
    ]

    readonly_fields = [
        'task_id',
        'created_at',
        'completed_at',
        'error_message'
    ]

    fieldsets = (
        ('Información General', {
            'fields': ('user', 'report_type', 'status')
        }),
        ('Tarea Asíncrona', {
            'fields': ('task_id', 'parameters')
        }),
        ('Archivo', {
            'fields': ('file',)
        }),
        ('Fechas', {
            'fields': ('created_at', 'completed_at')
        }),
        ('Errores', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
    )

    ordering = ['-created_at']
    date_hierarchy = 'created_at'

    def has_file(self, obj):
        return bool(obj.file)

    has_file.boolean = True
    has_file.short_description = 'Tiene archivo'

    def has_add_permission(self, request):
        return False
