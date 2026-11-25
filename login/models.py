from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Perfil(models.Model):
    TIPO_ADMINISTRADOR = 'administrador'
    TIPO_CLIENTE = 'cliente'
    TIPOS_USUARIO = [
        (TIPO_ADMINISTRADOR, 'Administrador'),
        (TIPO_CLIENTE, 'Cliente'),
    ]
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)

    tipo_usuario = models.CharField(
        max_length=20,
        choices=TIPOS_USUARIO,
        default=TIPO_CLIENTE,
    )

    def __str__(self):
        return f'Perfil de {self.usuario.username} - {self.tipo_usuario}'