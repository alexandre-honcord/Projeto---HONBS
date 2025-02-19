from django.apps import AppConfig
from django.db.models.signals import post_migrate

class HonbsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'honbs'

def create_fixed_fridges(sender, **kwargs):
    from honbs.models import Geladeira, Drawer

    fridge_names = ["Estação 1", "Estação 2", "Estação 3", "Estação 4", "Estação 5"]
    
    for name in fridge_names:
        fridge, created = Geladeira.objects.get_or_create(name=name)
        if created:
            for i in range(1, 6):  # Criando 5 gavetas para cada geladeira
                Drawer.objects.get_or_create(fridge=fridge, number=i)

class HonbsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "honbs"

    def ready(self):
        post_migrate.connect(create_fixed_fridges, sender=self)