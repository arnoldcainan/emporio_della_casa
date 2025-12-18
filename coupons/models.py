from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True, verbose_name="Código")
    valid_from = models.DateTimeField(verbose_name="Válido de")
    valid_to = models.DateTimeField(verbose_name="Válido até")
    discount = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Desconto (%)"
    )
    active = models.BooleanField(default=True, verbose_name="Ativo")
    usage_count = models.IntegerField(default=0, verbose_name="Vezes Usado")

    def __str__(self):
        return self.code