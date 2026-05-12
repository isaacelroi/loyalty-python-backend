from flask import Blueprint, jsonify, request
from redeemPoints_service import redeem_points_service

redeem_bp = Blueprint("redeem", __name__)


@redeem_bp.route("/redeem", methods=["POST"])
def redeem_api():

    data = request.json

    result = redeem_points_service(
        data["shop"],
        data["customer_id"]
    )

    return jsonify(result)
