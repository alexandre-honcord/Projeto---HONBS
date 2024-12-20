from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    IDtasy = models.IntegerField(null=True)
    name = models.CharField(max_length=100)
    username = models.CharField(max_length=50, unique=True)
    foto = models.ImageField(upload_to='users/photos/', null=True)
    last_login = models.DateTimeField(auto_now=True)

    # Corrigir conflitos com 'groups' e 'user_permissions'
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='honbs_user_set',  # Evita conflito com o modelo 'User' do Django
        blank=True
    )

    user_permissions = models.ManyToManyField(
        'auth.Permission',
        # Evita conflito com 'user_permissions' do Django
        related_name='honbs_user_permissions_set',
        blank=True
    )

    def __str__(self):
        return self.username
    
class Fridge(models.Model):
    nome = models.CharField(max_length=255, verbose_name="Nome da Geladeira") 
    quantidade_prateleiras = models.IntegerField(verbose_name="Quantidade de Prateleiras")

    def __str__(self):
        return self.nome


class HemocomponentStock(models.Model):
    fridge = models.ForeignKey(Fridge, on_delete=models.CASCADE, verbose_name="Geladeira")
    prateleira_id = models.IntegerField(verbose_name="ID da Prateleira")
    hemocomponente_id = models.IntegerField(verbose_name="ID do Hemocomponente")
    quantidade = models.IntegerField(verbose_name="Quantidade")

    def __str__(self):
        return f"Prateleira {self.prateleira_id} - Hemocomponente {self.hemocomponente_id}"
