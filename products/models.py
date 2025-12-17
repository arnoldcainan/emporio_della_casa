from django.db import models
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    # Atributos Gerais (Para qualquer produto futuro)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to='products/')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Atributos de Marketing/Filtro
    is_featured = models.BooleanField(default=False, verbose_name="Destaque na Home")
    is_promotion = models.BooleanField(default=False, verbose_name="Promoção")

    # Atributos Específicos para Vinhos (Podem ficar nulos para outros produtos)
    grape = models.CharField(max_length=100, blank=True, verbose_name="Uva")
    vintage = models.PositiveIntegerField(null=True, blank=True, verbose_name="Safra")
    winery = models.CharField(max_length=255, blank=True, verbose_name="Vinícola")
    country = models.CharField(max_length=100, blank=True, verbose_name="País")
    region = models.CharField(max_length=100, blank=True, verbose_name="Região")
    alcohol_content = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True,
                                          verbose_name="Teor Alcoólico")
    volume = models.CharField(max_length=50, blank=True, default="750ml")

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.vintage if self.vintage else 'N/A'})"