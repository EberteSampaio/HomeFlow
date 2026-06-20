from django.contrib.auth import views as auth_views
from django.urls import path

from apps.web import views

app_name = "web"

urlpatterns = [
    path(
        "entrar/",
        auth_views.LoginView.as_view(
            template_name="web/login.html", redirect_authenticated_user=True
        ),
        name="login",
    ),
    path("sair/", auth_views.LogoutView.as_view(), name="logout"),
    path("", views.dashboard, name="dashboard"),
    path("lancamentos/novo/", views.lancamento_novo, name="lancamento_novo"),
    path("lancamentos/divisao/", views.divisao_preview, name="divisao_preview"),
    path("parcelas/", views.installments, name="installments"),
    path("contas-do-mes/", views.despesas_mes, name="despesas_mes"),
    path("saldo/", views.settlements, name="settlements"),
    path(
        "saldo/rateio/<int:rateio_id>/pagar/",
        views.rateio_pagar,
        name="rateio_pagar",
    ),
]
