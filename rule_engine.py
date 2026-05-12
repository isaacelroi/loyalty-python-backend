from models import RewardRule


def calculate_rewards(shop, amount):
    try:
        rule = RewardRule.objects(
            shop=shop,
            trigger="order_paid",
            active=True
        ).first()

        if not rule:
            return 0

        if not rule.slab:
            return 0

        for slab in rule.slab:
            if slab.get("min", 0) <= amount <= slab.get("max", float("inf")):
                return slab.get("points", 0)

        return 0
    except Exception as e:
        print("Error in calculate_rewards:", e)
