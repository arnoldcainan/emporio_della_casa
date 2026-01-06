from django.contrib import admin
from .models import Course, Module, Lesson, LiveClass, LessonMaterial


# Configuração para editar Aulas DENTRO da tela de Módulo
class LessonInline(admin.StackedInline):
    model = Lesson
    extra = 1

class MaterialInline(admin.TabularInline):
    model = LessonMaterial
    extra = 1

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    inlines = [MaterialInline]
    list_display = ['title', 'module', 'order']
    list_filter = ['module__course', 'module']
    search_fields = ['title']

@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    inlines = [LessonInline]
    list_display = ['title', 'course', 'order']
    list_filter = ['course']

# Configuração para editar Módulos DENTRO da tela de Curso
class ModuleInline(admin.StackedInline):
    model = Module
    extra = 1

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    inlines = [ModuleInline]
    list_display = ['title', 'created_at']
    search_fields = ['title']

@admin.register(LiveClass)
class LiveClassAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'date_time', 'meet_link']
    list_filter = ['course', 'date_time']

