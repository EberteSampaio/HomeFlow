from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.accounts.models import (
    Casal,
    MembroCasal,
    RegraDivisao,
    RegraDivisaoItem,
    User,
)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("HomeFlow", {"fields": ("chave_pix",)}),
    )


class RegraDivisaoItemInline(admin.TabularInline):
    model = RegraDivisaoItem
    extra = 0


@admin.register(RegraDivisao)
class RegraDivisaoAdmin(admin.ModelAdmin):
    list_display = ("casal", "vigente_desde")
    inlines = [RegraDivisaoItemInline]


admin.site.register(Casal)
admin.site.register(MembroCasal)
