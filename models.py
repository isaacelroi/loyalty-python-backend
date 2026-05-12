from mongoengine import *
from datetime import datetime


# 👛 Wallet per customer per shop
class Wallet(Document):
    shop = StringField(required=True)
    customer_id = IntField(required=True)
    points_balance = FloatField(default=0)
    points_lifetime_earned = FloatField(default=0)
    points_lifetime_reversed = FloatField(default=0)
    tier = StringField(default="standard")
    status = StringField(default="active")
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    meta = {
        "indexes": [
            {"fields": ["shop", "customer_id"], "unique": True}
        ]
    }

# 📒 Ledger — source of truth
class WalletTxn(Document):
    shop = StringField(required=True)
    customer_id = IntField(required=True)
    txn_type = StringField(required=True)# credit | debit | refund | expire
    points_delta = FloatField(required=True)
    order_id = IntField()
    rule_code = StringField()
    reversed = BooleanField(default=False)
    reason = StringField()
    idempotency_key = StringField(unique=True, sparse=True, null=True)
    remaining_points = FloatField()
    created_at = DateTimeField(default=datetime.utcnow)

# ⚙️ Configurable rules
class RewardRule(Document):
    shop = StringField(required=True)
    code = StringField(required=True)
    trigger = StringField() # order_paid / signup / referral    
    slab = ListField(DictField())
    active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.utcnow)
    meta = {
        "indexes": [
            {"fields": ["shop", "code"], "unique": True},
            {"fields": ["shop", "trigger", "active"]}
        ]
    }
    

class RedemptionRule(Document):
    shop = StringField(required=True)
    code = StringField(required=True)
    points_required = IntField(required=True)
    discount_amount = FloatField(required=True)
    active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.utcnow)
    meta = {
        "indexes": [
            {"fields": ["shop", "code"], "unique": True},
            {"fields": ["shop", "active"]}
        ]
    }
    

class RedemptionReserve(Document):
    shop = StringField(required=True)
    customer_id = IntField(required=True)
    rule_code = StringField(required=True)
    points_required = FloatField(required=True)
    discount_amount = FloatField(required=True)
    discount_code = StringField()
    status = StringField() # reserved, completed, cancelled
    used_order_id = StringField()
    expires_at = DateTimeField(required=True)
    created_at = DateTimeField(default=datetime.utcnow)
    
    