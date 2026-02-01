from django.contrib import admin
from .models import Newsletter
import csv
from django.http import HttpResponse


@admin.register(Newsletter)
class NewsletterAdmin(admin.ModelAdmin):
    list_display = ('email', 'created_at_formatted')  # O que aparece na lista
    search_fields = ('email',)  # Barra de busca
    list_filter = ('created_at',)  # Filtro lateral por data
    ordering = ('-created_at',)  # Mais recentes primeiro

    # Adicionamos uma "Ação" personalizada para exportar
    actions = ['export_as_csv']

    def created_at_formatted(self, obj):
        return obj.created_at.strftime('%d/%m/%Y %H:%M')

    created_at_formatted.short_description = 'Data de Inscrição'

    @admin.action(description='Exportar E-mails para Excel/CSV')
    def export_as_csv(self, request, queryset):
        """
        Função que gera um arquivo CSV com os e-mails selecionados.
        Útil para importar em ferramentas de E-mail Marketing.
        """
        meta = self.model._meta
        field_names = ['email', 'created_at']

        response = HttpResponse(content_type='text/csv')
        # Adiciona BOM para o Excel abrir com acentos corretos (se houver)
        response.write(u'\ufeff'.encode('utf8'))
        response['Content-Disposition'] = f'attachment; filename={meta}.csv'
        writer = csv.writer(response)

        # Escreve o cabeçalho
        writer.writerow(['E-mail', 'Data de Inscrição'])


        # Escreve os dados
        for obj in queryset:
            writer.writerow([obj.email, obj.created_at.strftime('%d/%m/%Y %H:%M')])

        return response