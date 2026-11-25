from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect

from .models import Perfil


def is_administrator(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return Perfil.objects.filter(
        usuario_id=user.pk,
        tipo_usuario=Perfil.TIPO_ADMINISTRADOR,
    ).exists()


def administrator_required(view_func):
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not is_administrator(request.user):
            messages.error(request, "Apenas administradores podem acessar esta área.")
            return redirect("dashboard")
        return view_func(request, *args, **kwargs)

    return wrapped_view
