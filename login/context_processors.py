from .permissions import is_administrator


def user_role(request):
    return {"is_pixelcrate_admin": is_administrator(request.user)}
