from django.contrib import admin
from django.db.models import Sum, Avg, Count
from django.utils import timezone
from datetime import timedelta
from .models import Order, OrderItem, OrderDashboard, ShippingRate, OrderCourse, OrderWine


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    # Importante: permitir visualizar o curso ou produto no inline
    fields = ['product', 'course', 'price', 'quantity']
    readonly_fields = ['product', 'course']
    extra = 0

# --- 1. REMOVEMOS O @admin.register(Order) PARA EVITAR DUPLICIDADE ---

@admin.register(OrderWine)
class OrderWineAdmin(admin.ModelAdmin):
    """Admin focado exclusivamente em Vinhos com Logística Completa"""
    list_display = [
        'id', 'first_name', 'state', 'shipping_method',
        'status', 'tracking_code', 'estimated_delivery_date', 'paid', 'created'
    ]
    list_editable = ['status', 'tracking_code']
    list_filter = ['status', 'paid', 'state', 'created']
    search_fields = ['first_name', 'email', 'id']
    inlines = [OrderItemInline]

    # Reaproveitamos seus fieldsets originais aqui (com endereço e frete)
    fieldsets = (
        ('Informações do Cliente', {'fields': ('first_name', 'last_name', 'email', 'phone')}),
        ('Endereço de Entrega', {'fields': ('postal_code', 'address', 'city', 'state')}),
        ('Logística e Pagamento', {'fields': ('shipping_method', 'shipping_cost', 'paid', 'coupon', 'discount')}),
    )

    def get_queryset(self, request):
        # Filtro: Apenas pedidos que possuem produtos físicos (Vinhos)
        return super().get_queryset(request).filter(items__product__isnull=False).distinct()


# orders/admin.py

@admin.register(OrderCourse)
class OrderCourseAdmin(admin.ModelAdmin):
    """Admin focado exclusivamente em Cursos (Sem campos de frete/rastreio)"""
    list_display = ['id', 'first_name', 'email', 'paid', 'created']
    list_filter = ['paid', 'created']
    search_fields = ['first_name', 'email', 'id']
    inlines = [OrderItemInline]

    fieldsets = (
        ('Informações do Aluno', {'fields': ('first_name', 'last_name', 'email', 'phone')}),
        ('Pagamento do Curso', {'fields': ('paid', 'coupon', 'discount')}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).filter(items__course__isnull=False).distinct()

    # --- PASSO 3: LIBERAÇÃO MANUAL AO SALVAR NO ADMIN ---
    def save_model(self, request, obj, form, change):
        """
        Executa ao salvar o pedido no Admin. Se marcado como 'paid',
        tenta encontrar o usuário pelo e-mail e libera o curso.
        """
        # Primeiro, salva o pedido normalmente no banco de dados
        super().save_model(request, obj, form, change)

        # Se o pedido foi marcado como pago (paid=True)
        if obj.paid:
            from django.contrib.auth.models import User
            from financial.models import Enrollment

            try:
                # Busca o usuário pelo e-mail registrado no pedido
                user = User.objects.get(email__iexact=obj.email)

                # Percorre os itens do pedido para encontrar os cursos
                for item in obj.items.all():
                    if item.course:
                        # Cria ou atualiza a matrícula para status 'paid'
                        enrollment, created = Enrollment.objects.get_or_create(
                            student=user,
                            course=item.course,
                            defaults={'status': 'paid'}
                        )
                        if not created and enrollment.status != 'paid':
                            enrollment.status = 'paid'
                            enrollment.save()

                        print(f"✅ Curso '{item.course.title}' liberado manualmente para {user.email}")

            except User.DoesNotExist:
                print(f"⚠️ Aviso: Usuário com e-mail {obj.email} não encontrado. Curso não liberado.")
            except Exception as e:
                print(f"❌ Erro na liberação manual: {e}")


@admin.register(OrderDashboard)
class OrderDashboardAdmin(admin.ModelAdmin):
    # Seu código de Dashboard permanece igual, pois ele deve somar TUDO
    change_list_template = 'admin/sales_dashboard.html'

    def changelist_view(self, request, extra_context=None):
        last_30_days = timezone.now() - timedelta(days=30)
        orders = self.get_queryset(request).filter(created__gte=last_30_days)

        total_sales = sum(order.get_total_cost() for order in orders)
        count_orders = orders.count()
        avg_ticket = total_sales / count_orders if count_orders > 0 else 0

        top_coupons = orders.values('coupon__code').annotate(
            total=Count('id')
        ).order_by('-total')[:5]

        extra_context = extra_context or {}
        extra_context.update({
            'total_sales': total_sales,
            'avg_ticket': avg_ticket,
            'count_orders': count_orders,
            'top_coupons': top_coupons,
            'title': 'Relatório de Vendas Geral (30 dias)'
        })
        return super().changelist_view(request, extra_context=extra_context)

@admin.register(ShippingRate)
class ShippingRateAdmin(admin.ModelAdmin):
    list_display = ['state', 'pac_cost', 'sedex_cost', 'delivery_cost']
    list_editable = ['pac_cost', 'sedex_cost', 'delivery_cost']