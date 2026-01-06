from django.db import models
from django.contrib.auth.models import User
from courses.models import Course

class Enrollment(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    date_enrolled = models.DateTimeField(auto_now_add=True) # Nome padrão para evitar erros no Admin
    status = models.CharField(max_length=20, default='paid')

    def __str__(self):
        return f"{self.student.username} - {self.course.title}"