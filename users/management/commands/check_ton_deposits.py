from django.core.management.base import BaseCommand
from django.utils import timezone
import requests
from users.models import TonDepositRequest, User
from django.conf import settings

class Command(BaseCommand):
    help = 'Check TON deposit requests and credit balances'

    def handle(self, *args, **kwargs):
        TON_API_TOKEN = "AFTVO4WU53DURMIAAAAPFEGJ4KJR4WP5NK55EHL4NZHSKFQ52TBCLCFBDKNK3IMP4ACVIWI"
        WALLET_ADDRESS = settings.PROJECT_TON_WALLET

        deposits = TonDepositRequest.objects.filter(is_completed=False)
        if not deposits.exists():
            self.stdout.write(self.style.SUCCESS("Нет заявок"))
            return

        url = f"https://tonapi.io/v2/blockchain/accounts/{WALLET_ADDRESS}/transactions"
        headers = {"Authorization": f"Bearer {TON_API_TOKEN}"}
        response = requests.get(url, headers=headers)
        data = response.json()

        for tx in data.get('transactions', []):
            comment = tx['in_msg'].get('comment', '')
            amount_ton = int(tx['in_msg']['value']) / 1e9  # TON
            for deposit in deposits:
                if not deposit.is_completed and deposit.memo == comment and abs(float(deposit.amount) - amount_ton) < 0.00001:
                    user = deposit.user
                    user.ton_balance += deposit.amount
                    user.save(update_fields=["ton_balance"])
                    deposit.is_completed = True
                    deposit.completed_at = timezone.now()
                    deposit.tx_hash = tx['hash']
                    deposit.save()
                    self.stdout.write(self.style.SUCCESS(
                        f"Зачислено {deposit.amount} TON пользователю {user} (memo: {deposit.memo})"
                    ))
