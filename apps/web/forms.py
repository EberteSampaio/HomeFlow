"""Forms da web (validação/render; escrita vai pelos services)."""

from datetime import date, datetime

from django import forms
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Casal, MembroCasal
from apps.expenses.models import Categoria, Compra

_INPUT = (
    "w-full bg-surface-container-lowest border border-outline-variant rounded px-md py-sm "
    "text-body-md text-on-surface placeholder:text-outline "
    "focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/10 transition-colors"
)
_FILTRO = (
    "w-full bg-surface-container-lowest border border-outline-variant rounded px-md py-sm "
    "text-body-sm text-on-surface "
    "focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/10 transition-colors"
)


class LancamentoForm(forms.Form):
    descricao = forms.CharField(
        max_length=160,
        label="Título",
        widget=forms.TextInput(attrs={"class": _INPUT, "placeholder": "Ex.: Geladeira"}),
    )
    valor_total = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0.01,
        label="Valor (R$)",
        widget=forms.NumberInput(
            attrs={
                "class": _INPUT,
                "step": "0.01",
                "hx-get": "",  # preenchido no template (divisao_preview)
                "hx-target": "#divisao-card",
                "hx-trigger": "input changed delay:300ms",
                "hx-include": "[name='valor_total'],[name='data_compra']",
            }
        ),
    )
    categoria = forms.ModelChoiceField(
        queryset=Categoria.objects.none(),
        required=False,
        label="Categoria",
        widget=forms.Select(attrs={"class": _INPUT}),
    )
    data_compra = forms.DateField(
        label="Data",
        widget=forms.DateInput(attrs={"class": _INPUT, "type": "date"}),
    )
    pago_por = forms.ModelChoiceField(
        queryset=MembroCasal.objects.none(),
        label="Quem pagou",
        widget=forms.Select(attrs={"class": _INPUT}),
    )
    quantidade_parcelas = forms.IntegerField(
        min_value=1,
        initial=1,
        label="Nº de parcelas",
        help_text="Use 1 para despesa à vista.",
        widget=forms.NumberInput(attrs={"class": _INPUT, "min": "1"}),
    )
    primeira_data_vencimento = forms.DateField(
        label="1º vencimento",
        widget=forms.DateInput(attrs={"class": _INPUT, "type": "date"}),
    )

    def __init__(self, *args, casal: Casal, **kwargs):
        super().__init__(*args, **kwargs)
        self.casal = casal
        self.fields["categoria"].queryset = Categoria.objects.filter(casal=casal)
        self.fields["pago_por"].queryset = MembroCasal.objects.filter(
            casal=casal
        ).select_related("usuario")
        self.fields["pago_por"].label_from_instance = (
            lambda m: m.usuario.first_name or m.usuario.username
        )
        # URL do preview HTMX da Divisão Automática.
        self.fields["valor_total"].widget.attrs["hx-get"] = reverse(
            "web:divisao_preview"
        )
        if not self.is_bound:
            hoje = timezone.localdate()
            self.fields["data_compra"].initial = hoje
            self.fields["primeira_data_vencimento"].initial = hoje


class CompraFiltroForm(forms.Form):
    """Filtros do Painel (todos opcionais). Aplicados às despesas/gastos."""

    categoria = forms.ModelChoiceField(
        queryset=Categoria.objects.none(),
        required=False,
        empty_label="Todas",
        label="Categoria",
        widget=forms.Select(attrs={"class": _FILTRO}),
    )
    pago_por = forms.ModelChoiceField(
        queryset=MembroCasal.objects.none(),
        required=False,
        empty_label="Todos",
        label="Quem pagou",
        widget=forms.Select(attrs={"class": _FILTRO}),
    )
    mes = forms.CharField(
        required=False,
        label="Mês",
        widget=forms.DateInput(attrs={"class": _FILTRO, "type": "month"}),
    )
    status = forms.ChoiceField(
        required=False,
        label="Status",
        choices=[("", "Todos")] + list(Compra.Status.choices),
        widget=forms.Select(attrs={"class": _FILTRO}),
    )

    def __init__(self, *args, casal: Casal, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["categoria"].queryset = Categoria.objects.filter(casal=casal)
        self.fields["pago_por"].queryset = MembroCasal.objects.filter(
            casal=casal
        ).select_related("usuario")
        self.fields["pago_por"].label_from_instance = (
            lambda m: m.usuario.first_name or m.usuario.username
        )

    def clean_mes(self) -> date | None:
        """Converte 'YYYY-MM' (input type=month) no 1º dia do mês."""
        valor = self.cleaned_data.get("mes")
        if not valor:
            return None
        try:
            return datetime.strptime(valor, "%Y-%m").date().replace(day=1)
        except ValueError as exc:
            raise forms.ValidationError("Mês inválido (use AAAA-MM).") from exc
