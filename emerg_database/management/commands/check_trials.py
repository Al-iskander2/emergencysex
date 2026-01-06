# emerg_database/management/commands/check_trials.py
from django.core.management.base import BaseCommand
from logic.monitoring.monitoring import check_expired_trials

class Command(BaseCommand):
    help = 'Verifica y actualiza trials expirados (30 días)'

    def handle(self, *args, **options):
        self.stdout.write("🔍 Verificando trials expirados...")
        result = check_expired_trials()
        self.stdout.write(self.style.SUCCESS(f"Resultado: {result}"))