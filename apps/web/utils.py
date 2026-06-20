"""Helpers de UI (resolução do casal atual da sessão)."""

from apps.accounts.models import Casal


def get_casal_atual(request) -> Casal | None:
    """
    Casal do usuário autenticado, resolvido pelo seu MembroCasal.

    Cada pessoa só enxerga o próprio casal — não há fallback para "primeiro
    casal" (isso vazaria dados entre usuários). Retorna None se o usuário
    autenticado ainda não estiver vinculado a um casal (a UI mostra setup).
    As views são protegidas por @login_required, então aqui o usuário já é
    autenticado.
    """
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        membro = getattr(user, "membro", None)
        if membro is not None:
            return membro.casal
    return None
