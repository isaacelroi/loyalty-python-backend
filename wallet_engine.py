from models import Wallet
from datetime import datetime
import traceback
from db import init_db
init_db()


def get_wallet(shop, customer_id):
    print(f"Fetching wallet for {customer_id} in {shop}")
    try:
        wallet = Wallet.objects(
            shop=shop,
            customer_id=customer_id
        ).first()

        if not wallet:
            wallet = Wallet(
                shop=shop,
                customer_id=customer_id
            ).save()

        return wallet
    except Exception as e:
        print(traceback.format_exc())
        print("Error in get_wallet:", e)


def update_wallet_timestamp(wallet):
    wallet.updated_at = datetime.utcnow()
    wallet.save()
