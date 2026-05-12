import json
from redis_client import redis_conn
from rule_engine import calculate_rewards
from credit_engine import credit_wallet, reverse_refund_points
from credit_engine import reverse_order_points
from redeemPoints_service import handle_wallet_redemption_from_order, restore_redeemed_points_if_needed
from db import init_db
init_db()

print("🚀 Loyalty worker started")

while True:
    _, job = redis_conn.brpop("loyalty_queue")

    data = json.loads(job)

    print("Job:", data)

    try:
        if data["type"] == "order_paid":

            customer_id = data.get("customerId")

            if not customer_id:
                print(" Missing customerId — skip")
                continue

            points = calculate_rewards(data["shop"], float(data["total"]))

            print("Rewards:", points)

            credit_wallet(
                shop=data["shop"],
                customer_id=customer_id,
                points=points,
                order_id=data["orderId"]
            )
            handle_wallet_redemption_from_order(data)
            print("Done processing job...")
            
        if data["type"] == "order_cancelled":
            reverse_order_points(
                shop=data["shop"],
                order_id=data["orderId"]
            )
            print("Order cancelled — no action taken (debit logic not implemented)")
            
        if data["type"] == "refund_create":
            print("Processing refund job")
            reverse_refund_points(
                shop=data["shop"],
                order_id=data["orderId"],
                refund_amount=float(data["refundAmount"])
            )

            restore_redeemed_points_if_needed(
                shop=data["shop"],
                order_id=data["orderId"]
            )

            print("Refund processed")


    except Exception as e:
        print("Worker error:", e)

