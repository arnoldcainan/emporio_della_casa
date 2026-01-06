from django.contrib import admin
from .models import Order, OrderItem,OrderDashboard, ShippingRate

from django.db.models import Sum, Avg, Count
from django.utils import timezone
from datetime import timedelta


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ['product']
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    # Colunas que aparecem na listagem principal
    list_display = [
        'id', 'first_name', 'last_name', 'email',
        'state', 'shipping_method','estimated_delivery_date', 'shipping_cost',
        'paid', 'created'
    ]

    # Filtros laterais para facilitar a gestão
    list_filter = ['paid', 'shipping_method', 'state', 'created', 'updated']

    # Busca rápida por nome, email ou ID do pedido
    search_fields = ['first_name', 'last_name', 'email', 'id']

    # Itens do pedido aparecem dentro da página do pedido
    inlines = [OrderItemInline]

    # Organização dos campos ao abrir o pedido (Fieldsets)
    fieldsets = (
        ('Informações do Cliente', {
            'fields': ('first_name', 'last_name', 'email', 'phone')
        }),
        ('Endereço de Entrega', {
            'fields': ('postal_code', 'address', 'city', 'state')
        }),
        ('Logística e Pagamento', {
            'fields': ('shipping_method', 'shipping_cost', 'paid', 'coupon', 'discount')
        }),
    )


@admin.register(OrderDashboard)
class OrderDashboardAdmin(admin.ModelAdmin):
    change_list_template = 'admin/sales_dashboard.html'

    def changelist_view(self, request, extra_context=None):
        # Filtros de tempo (Últimos 30 dias)
        last_30_days = timezone.now() - timedelta(days=30)
        orders = self.get_queryset(request).filter(created__gte=last_30_days)

        # 1. Cálculos Manuais (Já que o total é dinâmico)
        total_sales = 0
        for order in orders:
            # Usando o método que já existe no seu modelo Order
            total_sales += order.get_total_cost()

        count_orders = orders.count()
        avg_ticket = total_sales / count_orders if count_orders > 0 else 0

        # 2. Uso de Cupons (Isso funciona pois 'coupon' é um campo)
        top_coupons = orders.values('coupon__code').annotate(
            total=Count('id')
        ).order_by('-total')[:5]

        extra_context = extra_context or {}
        extra_context.update({
            'total_sales': total_sales,
            'avg_ticket': avg_ticket,
            'count_orders': count_orders,
            'top_coupons': top_coupons,
            'title': 'Relatório de Vendas (30 dias)'
        })
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(ShippingRate)
class ShippingRateAdmin(admin.ModelAdmin):
    list_display = ['state', 'pac_cost', 'sedex_cost', 'delivery_cost']
    list_editable = ['pac_cost', 'sedex_cost', 'delivery_cost']
    search_fields = ['state']