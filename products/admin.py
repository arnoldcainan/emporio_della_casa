from django.contrib import admin
from .models import Category, Product

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'stock', 'is_active', 'is_featured']
    list_filter = ['is_active', 'category', 'is_featured', 'country', 'grape']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}