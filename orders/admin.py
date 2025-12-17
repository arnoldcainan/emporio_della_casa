from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ['product']
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    # Colunas que aparecerão na lista principal
    list_display = ['id', 'first_name', 'city', 'shipping_cost', 'get_total_cost', 'paid', 'created']

    # Filtros laterais para facilitar a gestão
    list_filter = ['paid', 'created', 'updated', 'utm_source']

    # Itens do pedido aparecem dentro da página do pedido
    inlines = [OrderItemInline]

    # Organização dos campos no formulário de edição
    fieldsets = (
        ('Informações do Cliente', {
            'fields': ('first_name', 'last_name', 'email', 'address', 'postal_code', 'city')
        }),
        ('Financeiro', {
            'fields': ('shipping_cost', 'paid')  # <-- Inclua shipping_cost aqui
        }),
        ('Rastreamento de Marketing (UTM)', {
            'fields': ('utm_source', 'utm_medium', 'utm_campaign'),
        }),
    )

    def get_total_cost(self, obj):
        return f"R$ {obj.get_total_cost()}"
    get_total_cost.short_description = 'Total (c/ Frete)'