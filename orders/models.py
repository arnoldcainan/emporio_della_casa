from django.db import models
from django.core.validators import MinLengthValidator
from products.models import Product
from decimal import Decimal
from coupons.models import Coupon
from datetime import timedelta


class Order(models.Model):
    SHIPPING_CHOICES = [
        ('pac', 'PAC'),
        ('sedex', 'SEDEX'),
        ('delivery', 'Transportadora'),
    ]
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField()
    # O formato (00) 00000-0000 possui 15 caracteres
    phone = models.CharField(
        'WhatsApp',
        max_length=20,
        validators=[MinLengthValidator(15, message="O número de WhatsApp está incompleto.")]
    )
    address = models.CharField(max_length=250)
    postal_code = models.CharField(
        'CEP',
        max_length=20,
        validators=[MinLengthValidator(8, message="O CEP deve conter 8 dígitos.")]
    )

    city = models.CharField('Cidade', max_length=100)
    state = models.CharField('UF', max_length=2)

    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    shipping_method = models.CharField(
        'Método de Envio',
        max_length=20,
        choices=SHIPPING_CHOICES,
        default='pac'
    )

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    paid = models.BooleanField(default=False)

    # Rastreamento de Marketing (UTM)
    utm_source = models.CharField(max_length=100, blank=True, null=True)
    utm_medium = models.CharField(max_length=100, blank=True, null=True)
    utm_campaign = models.CharField(max_length=100, blank=True, null=True)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    coupon = models.ForeignKey(Coupon,
                               related_name='orders',
                               null=True,
                               blank=True,
                               on_delete=models.SET_NULL)
    discount = models.IntegerField(default=0)

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return f'Pedido {self.id}'

    def get_total_cost(self):
        total_items = sum(item.get_cost() for item in self.items.all())
        # Aplica o desconto se houver
        discount_amount = total_items * (Decimal(self.discount) / Decimal(100))
        return (total_items - discount_amount) + Decimal(self.shipping_cost)

    @property
    def estimated_delivery_date(self):
        """Calcula a entrega somente se o pedido estiver pago"""
        if not self.paid:
            return None  # Não exibe data se não houver confirmação de pagamento

        try:
            rate = ShippingRate.objects.get(state__iexact=self.state)

            days = 0
            if self.shipping_method == 'sedex':
                days = rate.sedex_days
            elif self.shipping_method == 'delivery':
                days = rate.delivery_days
            else:
                days = rate.pac_days

            # A contagem começa a partir da última atualização (confirmação do Webhook)
            return self.updated + timedelta(days=days)
        except ShippingRate.DoesNotExist:
            return None


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='order_items', on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Preço histórico
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return str(self.id)

    def get_cost(self):
        return self.price * self.quantity


class OrderDashboard(Order):
    class Meta:
        proxy = True
        verbose_name = 'Dashboard de Vendas'
        verbose_name_plural = 'Dashboard de Vendas'


class ShippingRate(models.Model):
    state = models.CharField('Estado (UF)', max_length=2, unique=True)

    # PAC
    pac_cost = models.DecimalField('Custo PAC', max_digits=10, decimal_places=2)
    pac_days = models.PositiveIntegerField('Prazo PAC (dias)')

    # SEDEX
    sedex_cost = models.DecimalField('Custo SEDEX', max_digits=10, decimal_places=2)
    sedex_days = models.PositiveIntegerField('Prazo SEDEX (dias)')

    # Transportadora
    delivery_cost = models.DecimalField('Custo Transportadora', max_digits=10, decimal_places=2)
    delivery_days = models.PositiveIntegerField('Prazo Transportadora (dias)')

    def __str__(self):
        return f"Fretes para {self.state}"

    class Meta:
        verbose_name = 'Tabela de Frete'
        verbose_name_plural = 'Tabelas de Fretes'