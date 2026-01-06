from django.contrib import admin
from .models import Enrollment

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    # Remova 'amount' e 'created_at'. Use 'date_enrolled'
    list_display = ['student', 'course', 'status', 'date_enrolled']
    list_filter = ['status', 'course', 'date_enrolled']
    search_fields = ['student__username', 'course__title']