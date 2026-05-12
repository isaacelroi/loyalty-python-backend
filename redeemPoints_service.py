import requests,traceback
from uuid import uuid4
from models import RedemptionRule, WalletTxn,RedemptionReserve,Wallet
from datetime import datetime, timedelta
from wallet_engine import get_wallet
from twilio.rest import Client
import os
from db import init_db
init_db()



client = Client(
    os.getenv("TWILIO_ACCOUNT_SID"),
    os.getenv("TWILIO_AUTH_TOKEN")
)
ACTIVE_REUSE_DAYS = 30
DISCOUNT_VALID_DAYS = 45

# WATI_API = "https://app-server.wati.io"
# WATI_KEY = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiI2NWJjZGY0MC01Y2JlLTQxYmUtYjg4OC1kNDc1MmFmNTBjNTQiLCJ1bmlxdWVfbmFtZSI6InNoYW5rYXJAZWxyb2kuaW8iLCJuYW1laWQiOiJzaGFua2FyQGVscm9pLmlvIiwiZW1haWwiOiJzaGFua2FyQGVscm9pLmlvIiwiYXV0aF90aW1lIjoiMDIvMTcvMjAyNiAxMzowNjoxNiIsImRiX25hbWUiOiJ3YXRpX2FwcF90cmlhbCIsImh0dHA6Ly9zY2hlbWFzLm1pY3Jvc29mdC5jb20vd3MvMjAwOC8wNi9pZGVudGl0eS9jbGFpbXMvcm9sZSI6IlRSSUFMIiwiZXhwIjoxNzcxOTc3NjAwLCJpc3MiOiJDbGFyZV9BSSIsImF1ZCI6IkNsYXJlX0FJIn0.qHfm9XaAMNI23AhX8JFgaMVVRTLN4_L62OVtsYNM9s4"

WATI_API = os.getenv("WATI_API")
WATI_KEY = os.getenv("WATI_KEY")
def redeem_points_service(shop, customer_id):
    try:
        now = datetime.utcnow()
        wallet = get_wallet(shop, customer_id)
        print("wallet balance:", wallet.points_balance)
        rule = get_best_redemption_rule(shop, wallet.points_balance)
        print("rule", rule)

        if not rule:
            return {"error": "Not enough points"}
        
        # Auto-expire old pending reserves
        
        expired_reserves = RedemptionReserve.objects(
            shop=shop,
            customer_id=customer_id,
            status="pending",
            expires_at__lte=now
        )

        for r in expired_reserves:
            r.status = "expired"
            r.expired_at = now
            r.save()
            print("Marked expired:", r.discount_code)

        # ---------------------------------------
        # 4️⃣ Check active reserve
        # ---------------------------------------
        active_reserve = RedemptionReserve.objects(
            shop=shop,
            customer_id=customer_id,
            status="pending",
            expires_at__gt=now
        ).order_by("-created_at").first()

        if active_reserve:

            days_left = (active_reserve.expires_at - now).days
            print("Active reserve days left:", days_left)

            # ✅ reuse if still strongly valid
            if days_left >= ACTIVE_REUSE_DAYS:
                return {
                    "success": True,
                    "message": "Existing discount still valid",
                    "code": active_reserve.discount_code,
                    "reuse": True,
                    "expires_at": active_reserve.expires_at.isoformat()
                }
        
        try:
            url = "https://shopify.elroi.io/api/create-discount"
            token = os.getenv("SHOPIFY_API_KEY")
            payload = {
                "shop": shop,
                "customerId": customer_id,
                "amount": rule.discount_amount
            }
            resp = requests.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {token}"}
            )
        except Exception as e:
            print(traceback.format_exc())
            print("Error calling discount API:", e)
            return {"error": "Failed to create discount"}

        if resp.status_code != 200:
            print("Discount API error:", resp.status_code, resp.text)
            return {"error": "discount creation failed"}
        
        discount_data = resp.json()
        code = discount_data.get("code")
        if not code:
            return {"error": "Invalid discount response"}
        
        reserve = RedemptionReserve(
            shop=shop,
            customer_id=customer_id,
            rule_code=rule.code,
            points_required=rule.points_required,
            discount_amount=rule.discount_amount,
            discount_code=code,
            status="pending",
            expires_at=now + timedelta(days=DISCOUNT_VALID_DAYS)
        ).save()

        # ✅ send message
        # send_discount_email(customer_id, code, rule.discount_amount)
        # send_whatsapp_discount("+919751118289", code, rule.discount_amount)
        result = send_wati_discount("919751118289", code, rule.discount_amount)
        print("WATI result:", result)
        if  result.get("result") == False:
            print("Failed to send WATI message:", result)
            return {"error": "Failed to send discount message"}
        
        # deduct points
        wallet.points_balance -= rule.points_required
        wallet.save()
        
        # # ledger
        WalletTxn(
            shop=shop,
            customer_id=customer_id,
            txn_type="redeem",
            points_delta=-rule.points_required,
            reason="discount_redeem",
            rule_code=rule.code,
            idempotency_key=f"redeem:{shop}:{customer_id}:{rule.code}:{uuid4().hex}"
        ).save()
        
        return {
            "success": True,
            "message": "New discount created",
            "code": code,
            "points_used": rule.points_required,
            "expires_at": reserve.expires_at.isoformat(),
            "reuse": False
        }
    except Exception as e:
        print(traceback.format_exc())
        print("Error in redeem_points_service:", e)


def get_best_redemption_rule(shop, points):
    return RedemptionRule.objects(
        shop=shop,
        active=True,
        points_required__lte=points
    ).order_by("-points_required").first()


def handle_wallet_redemption_from_order(order):
    try:
        print("Handling wallet redemption for order", order)
        shop = order["shop"]
        if not order.get("customerId"):
            return

        customer_id = order["customerId"]

        for d in order.get("discount_codes", []):
            code = d["code"]
            print("code", code)

            reserve = RedemptionReserve.objects(
                shop=shop,
                discount_code=code,
                status="pending"
            ).first()

            if not reserve:
                continue

            # ✅ idempotent check
            if reserve.used_order_id:
                continue

            # wallet = get_wallet(shop, customer_id)

            # if wallet.points_balance < reserve.points_required:
            #     print("warning: insufficient balance at payment time")

            # # deduct now
            # wallet.points_balance -= reserve.points_required
            # wallet.save()

            # mark used
            reserve.status = "used"
            reserve.used_order_id = str(order["orderId"])
            reserve.save()

            # ledger
            # WalletTxn(
            #     shop=shop,
            #     customer_id=customer_id,
            #     txn_type="redeem",
            #     points_delta=-reserve.points_required,
            #     reason="discount_used",
            #     rule_code=reserve.rule_code,
            #     idempotency_key=f"redeem:{shop}:{customer_id}:{reserve.rule_code}:{uuid4().hex}"
            # ).save()
    except Exception as e:
        print(traceback.format_exc())
        print("Error in handle_wallet_redemption_from_order:", e)
        



def restore_redeemed_points_if_needed(shop, order_id):
    try:
        
        reserve = RedemptionReserve.objects(
            shop=shop,
            used_order_id=order_id,
            status="used"
        ).first()

        if not reserve:
            return

        wallet = Wallet.objects(
            shop=shop,
            customer_id=reserve.customer_id
        ).first()

        wallet.points_balance += reserve.points_required
        wallet.save()

        reserve.status = "refunded"
        reserve.save()

        print("Restored redeemed points")
    except Exception as e:
        print(traceback.format_exc())
        print("Error in restore_redeemed_points_if_needed:", e)



def send_whatsapp_discount(phone, code, amount):
    try:
        print(f"Sending WhatsApp to {phone} with code {code} and amount {amount}")
        msg = f"""
        🎁 Loyalty Reward Unlocked!

        Code: {code}
        Discount: ${amount}

        Use at checkout.
        """

        message = client.messages.create(
            from_="whatsapp:+14155238886",   # Twilio sandbox
            to=f"whatsapp:{phone}",
            body=msg
        )

        print("WhatsApp sent:", message.sid)
    except Exception as e:
        print(traceback.format_exc())
        print("Error sending WhatsApp:", e)
        
def send_wati_discount(phone, code, amount):
    try:
        print(f"Sending WATI WhatsApp to {phone} with code {code} and amount {amount}")

        # url = f"{WATI_API}/api/v1/sendSessionMessage/{phone}"
        # message_content = f"🎁 Loyalty Reward Ready!\n\nCode: {code}\nDiscount: ${amount}\n\nUse at checkout."

        # headers = {
        #     "Authorization": f"{WATI_KEY}",
        #     "Content-Type": "application/json"
        # }

        # params = {
        #     "messageText": message_content
        # }

        # r = requests.post(url, params=params, headers=headers)
        # print("result", r)
        # print("WATI status:", r.status_code, r.text)

        # return r.json()
        url = f"{WATI_API}/api/v2/sendTemplateMessage"

        headers = {
            "Authorization": f"Bearer {WATI_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "template_name": "loyalty_reward",       # must match your approved template name
            "broadcast_name": f"loyalty_{phone}",    # any unique name for tracking
            "parameters": [
                {"name": "code", "value": str(code)},
                {"name": "amount", "value": str(amount)}
            ]
        }

        params = {"whatsappNumber": phone}  # phone goes as query param

        r = requests.post(url, params=params, json=payload, headers=headers)
        print("WATI status:", r.status_code, r.text)

        response_data = r.json()

        # Check for errors
        if not response_data.get("result"):
            print("WATI Error:", response_data.get("error") or response_data.get("info"))

        return response_data
    except Exception as e:
        print(traceback.format_exc())
        print("Error sending WATI WhatsApp:", e)