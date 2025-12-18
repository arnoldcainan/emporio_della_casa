from django.contrib import admin
from .models import Coupon


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    # Colunas que aparecerão na listagem
    list_display = ['code', 'valid_from', 'valid_to', 'discount', 'active', 'usage_count']

    # Filtros na lateral direita
    list_filter = ['active', 'valid_from', 'valid_to']

    # Campo de busca (útil quando você tiver muitos cupons)
    search_fields = ['code']

    # Permite editar o campo 'active' direto na listagem sem entrar no cupom
    list_editable = ['active']

    # Ordenação padrão (mais novos primeiro)
    ordering = ['-valid_from']