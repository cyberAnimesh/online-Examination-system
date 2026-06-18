from django.contrib import admin

# Register your models here.

from .models import Category

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at', 'updated_at']
    search_fields = ['name']
    list_filter = ['created_at', 'updated_at']
    prepopulated_fields = {'name': ('name',)}
    ordering = ['created_at']