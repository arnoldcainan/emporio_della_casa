from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ['product']
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    # Colunas que aparecerão na lista principal
    list_display = ['id', 'first_name', 'last_name', 'email',
                    'paid', 'created', 'utm_source', 'utm_campaign']

    # Filtros laterais para facilitar a gestão
    list_filter = ['paid', 'created', 'updated', 'utm_source']

    # Itens do pedido aparecem dentro da página do pedido
    inlines = [OrderItemInline]

    # Organização dos campos no formulário de edição
    fieldsets = (
        ('Informações do Cliente', {
            'fields': ('first_name', 'last_name', 'email', 'address', 'postal_code', 'city')
        }),
        ('Status do Pagamento', {
            'fields': ('paid',)
        }),
        ('Rastreamento de Marketing (UTM)', {
            'fields': ('utm_source', 'utm_medium', 'utm_campaign'),
            'description': 'Dados capturados pelo middleware de marketing'
        }),
    )