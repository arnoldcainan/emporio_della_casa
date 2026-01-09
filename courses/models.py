from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings
import re
import os

class Course(models.Model):
    title = models.CharField("Título", max_length=200)
    description = models.TextField("Descrição", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    price = models.DecimalField("Preço", max_digits=10, decimal_places=2, default=0.00)
    image = models.ImageField("Capa do Curso", upload_to='courses/covers/', blank=True, null=True)
    is_active = models.BooleanField(default=True)

    # NOVO CAMPO: Imagem de fundo do certificado
    certificate_template = models.ImageField(
        upload_to='certificate_templates/',
        blank=True,
        null=True,
        help_text="Envie uma imagem (JPG/PNG) tamanho A4 paisagem para ser o fundo"
    )

    def __str__(self):
        return self.title

class Module(models.Model):
    course = models.ForeignKey(Course, related_name='modules', on_delete=models.CASCADE)
    title = models.CharField("Título do Módulo", max_length=200)
    order = models.PositiveIntegerField("Ordem", help_text="1 para primeiro, 2 para segundo...")

    class Meta:
        ordering = ['order']
        verbose_name = "Módulo"
        verbose_name_plural = "Módulos"

    def __str__(self):
        return f"{self.course.title} - {self.title}"


class Lesson(models.Model):
    module = models.ForeignKey(Module, related_name='lessons', on_delete=models.CASCADE)
    title = models.CharField("Título da Aula", max_length=200)
    video_url = models.URLField("Link do Vídeo", blank=True, null=True)
    content = models.TextField("Conteúdo/Resumo", blank=True)
    order = models.PositiveIntegerField("Ordem", default=1)

    class Meta:
        ordering = ['order']
        verbose_name = "Aula"
        verbose_name_plural = "Aulas"

    def __str__(self):
        return self.title

    @property
    def get_video_type(self):
        """Identifica qual é a plataforma de vídeo"""
        if not self.video_url:
            return None
        if 'youtu' in self.video_url:
            return 'youtube'
        if 'vimeo' in self.video_url:
            return 'vimeo'
        if 'bunnycdn' in self.video_url or 'b-cdn' in self.video_url or 'mediadelivery' in self.video_url:
            return 'bunny'
        return 'unknown'

    def get_video_id(self):
        """Extrai o ID ou URL correta para o Embed"""
        if not self.video_url:
            return None

        # Lógica para YouTube (Regex atualizado e blindado contra ?si=)
        if self.get_video_type == 'youtube':
            # Procura por v=, embed/, ou a barra final de um link curto, seguido de 11 chars
            regex = r'(?:v=|be\/|embed\/|shorts\/)([0-9A-Za-z_-]{11})'
            match = re.search(regex, self.video_url)
            return match.group(1) if match else None

        # ... mantenha o resto do código para Vimeo e Bunny ...
        if self.get_video_type == 'vimeo':
            regex = r'vimeo\.com/(?:.*#|.*/videos/)?([0-9]+)'
            match = re.search(regex, self.video_url)
            return match.group(1) if match else None

        if self.get_video_type == 'bunny':
            return self.video_url

        return None


class LessonMaterial(models.Model):
    lesson = models.ForeignKey(Lesson, related_name='materials', on_delete=models.CASCADE)
    title = models.CharField("Título do Material", max_length=100)
    file = models.FileField("Arquivo", upload_to='course_materials/')

    class Meta:
        verbose_name = "Material Complementar"
        verbose_name_plural = "Materiais Complementares"

    def __str__(self):
        return self.title

    @property
    def extension(self):
        # Retorna a extensão do arquivo (pdf, docx, etc)
        name, extension = os.path.splitext(self.file.name)
        return extension.lower().replace('.', '')


class LiveClass(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='live_classes')
    title = models.CharField("Assunto da Live", max_length=200)
    meet_link = models.URLField("Link do Meet")
    date_time = models.DateTimeField("Data e Hora")

    class Meta:
        ordering = ['date_time']
        verbose_name = "Aula ao Vivo"
        verbose_name_plural = "Aulas ao Vivo"

    def __str__(self):
        return f"{self.title} - {self.date_time}"

    @property
    def is_active(self):
        return self.date_time >= timezone.now()


class LessonView(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='views')
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'lesson')

    def __str__(self):
        return f"{self.student} viu {self.lesson}"
