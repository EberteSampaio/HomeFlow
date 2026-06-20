from django.contrib import admin

from apps.expenses.models import (
    Categoria,
    Compra,
    DespesaRecorrente,
    Parcela,
    Rateio,
)


class ParcelaInline(admin.TabularInline):
    model = Parcela
    extra = 0


@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):
    list_display = ("descricao", "valor_total", "quantidade_parcelas", "pago_por", "status", "origem")
    list_filter = ("status", "origem")
    inlines = [ParcelaInline]


@admin.register(Rateio)
class RateioAdmin(admin.ModelAdmin):
    list_display = ("parcela", "membro", "percentual_aplicado", "valor_devido", "status_pagamento")
    list_filter = ("status_pagamento",)


admin.site.register(Categoria)
admin.site.register(Parcela)
admin.site.register(DespesaRecorrente)
