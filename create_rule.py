
from flask import Blueprint, jsonify, request
from models import RewardRule,RedemptionRule
from datetime import datetime
from db import init_db
init_db()

import traceback


create_reward_bp = Blueprint("create_reward", __name__)
create_redemption_bp = Blueprint("create_redemption", __name__)



def _as_bool(value, default=False):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes"}
    if value is None:
        return default
    return bool(value)

@create_reward_bp.route("/create_reward", methods=["POST"])
def create_reward_api():
    try:
        data = request.json or {}
        active = _as_bool(data.get("active", True), default=True)
        shop = data["shop"]
        if active:
            RewardRule.objects(shop=shop, active=True).update(active=False)

        rule = RewardRule(
            shop=shop,
            code=data["code"],
            trigger="order_paid",
            slab=data.get("slab", []),
            active=active
        )

        rule.save()
        print("✅ Reward rule created:", rule.code)
        return jsonify({"message": "Reward rule created"}), 200        
    
    except Exception as e:
        print(traceback.format_exc())
        print("Error in create_reward_api:", e)
        return jsonify({"error": str(e)}), 400
    
    

@create_redemption_bp.route("/create_redemption", methods=["POST"])
def create_redemption_api():
    try:
        data = request.json or {}
        active = _as_bool(data.get("active", True), default=True)
        shop = data["shop"]
        if active:
            RedemptionRule.objects(shop=shop, active=True).update(active=False)

        rule = RedemptionRule(
            shop=shop,
            code=data["code"],
            points_required=data["points_required"],
            discount_amount=data["discount_amount"],
            active=active
        )

        rule.save()
        print("✅ Redemption rule created:", rule.code)
        return jsonify({"message": "Redemption rule created"}), 200
    except Exception as e:
        print(traceback.format_exc())
        print("Error in create_redemption_api:", e)
        return jsonify({"error": str(e)}), 400
