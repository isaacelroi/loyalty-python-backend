from models import WalletTxn,Wallet
from wallet_engine import get_wallet
from datetime import datetime
import traceback


def credit_wallet(shop, customer_id, points, order_id):
    try:
        print(f"Crediting wallet for {customer_id} in {shop} with amount {points}")

        wallet = get_wallet(shop, customer_id)

        wallet.points_balance += points
        wallet.points_lifetime_earned += points
        wallet.save()

        idempotency_key = None
        if order_id is not None:
            idempotency_key = f"credit:{shop}:{customer_id}:{order_id}"

        if idempotency_key:
            existing = WalletTxn.objects(idempotency_key=idempotency_key).first()
            if existing:
                print("Duplicate credit ignored for idempotency_key:", idempotency_key)
                return

        WalletTxn(
            shop=shop,
            customer_id=customer_id,
            txn_type="credit",
            points_delta=points,
            order_id=order_id,
            idempotency_key=idempotency_key
        ).save()

        print("credited", points)
    except Exception as e:
        print(traceback.format_exc())
        print("Error in credit_wallet:", e)
        

def reverse_order_points(shop, order_id):
    """
    Reverse all points credits issued for an order
    """
    try:
        print(f"Reversing points for order {order_id} in {shop}")
        credit_txns = WalletTxn.objects(
            shop=shop,
            order_id=order_id,
            txn_type="credit",
            reversed=False
        )

        if not credit_txns:
            print("No point credits found for order", order_id)
            return

        for txn in credit_txns:
            wallet = Wallet.objects(
                shop=shop,
                customer_id=txn.customer_id
            ).first()

            if not wallet:
                continue

            # safety — prevent negative points
            reverse_points = min(wallet.points_balance, txn.points_delta)
            print(f"Reversing {reverse_points} points for customer {txn.customer_id}")
            # update wallet
            wallet.points_balance -= reverse_points
            wallet.points_lifetime_reversed += reverse_points
            wallet.updated_at = datetime.utcnow()
            wallet.save()

            # mark original txn reversed
            txn.reversed = True
            txn.save()

            # create reversal ledger entry
            WalletTxn(
                shop=shop,
                customer_id=txn.customer_id,
                txn_type="points_reverse",
                points_delta=-reverse_points,
                order_id=order_id,
                reason="order_cancelled",
                idempotency_key=f"cancel-{txn.id}",
                remaining_points=wallet.points_balance
            ).save()

            print("Reversed points:", reverse_points)
    except Exception as e:
        print(traceback.format_exc())
        print("Error in reverse_order_points:", e)


def reverse_refund_points(shop, order_id, refund_amount):
    try:
        earn_txn = WalletTxn.objects(
            shop=shop,
            order_id=order_id,
            txn_type="earn"
        ).first()

        if not earn_txn:
            print("No earn txn found")
            return

        order_total = earn_txn.meta.get("order_total")

        if not order_total:
            print("Missing order total meta")
            return

        ratio = min(refund_amount / order_total, 1)

        points_to_reverse = int(earn_txn.points_delta * ratio)

        wallet = Wallet.objects(
            shop=shop,
            customer_id=earn_txn.customer_id
        ).first()

        wallet.points_balance -= points_to_reverse
        wallet.save()

        WalletTxn(
            shop=shop,
            customer_id=earn_txn.customer_id,
            txn_type="refund_reverse",
            points_delta=-points_to_reverse,
            order_id=order_id,
            reason="refund",
            meta={"refund_amount": refund_amount}
        ).save()

        print("Reversed points:", points_to_reverse)
    except Exception as e:
        print(traceback.format_exc())
        print("Error in reverse_refund_points:", e)
