from flask import Flask, jsonify
import db
from wallet_engine import get_wallet
from redeem import redeem_bp
from create_rule import create_reward_bp
from create_rule import create_redemption_bp
from flask_cors import CORS

app = Flask(__name__)

CORS(app)
app.register_blueprint(redeem_bp)
app.register_blueprint(create_reward_bp)
app.register_blueprint(create_redemption_bp)

@app.route("/wallet/<shop>/<customer_id>")
def wallet_balance(shop, customer_id):
    wallet = get_wallet(shop, customer_id)

    return jsonify({
        "balance": wallet.points_balance,
        "lifetimeEarned": wallet.points_lifetime_earned,
        "lifetimeReversed": wallet.points_lifetime_reversed,
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0",port=5001)
