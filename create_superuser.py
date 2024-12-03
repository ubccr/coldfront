import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "coldfront.config.settings")

django.setup()

from django.contrib.auth.models import User

def create_superuser():
    # Leggi le variabili di ambiente
    username = os.getenv('DJANGO_SUPERUSER_USERNAME', 'superuser')
    email = os.getenv('DJANGO_SUPERUSER_EMAIL', 'mail@mail.example')
    password = os.getenv('DJANGO_SUPERUSER_PASSWORD', 'password')
    
    # Crea o aggiorna l'utente super
    User.objects.create_superuser(username, email, password)

if __name__ == '__main__':
    create_superuser()
