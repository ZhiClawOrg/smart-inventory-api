from flask import Blueprint, request, jsonify
from app import db
from app.models.product import Product
from app.models.order import Order

orders_bp = Blueprint("orders", __name__)


@orders_bp.route("/orders", methods=["POST"])
def create_order():
    data = request.get_json(silent=True) or {}

    required_fields = ["product_id", "quantity"]
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return (
            jsonify(
                {"error": f"Missing required fields: {', '.join(sorted(missing_fields))}"}
            ),
            400,
        )

    product_id = data.get("product_id")
    quantity = data.get("quantity")

    if (
        not isinstance(product_id, int)
        or isinstance(product_id, bool)
        or product_id <= 0
    ):
        return jsonify({"error": "product_id must be a positive integer"}), 400

    if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
        return jsonify({"error": "Quantity must be a positive integer"}), 400

    product = Product.query.get(product_id)
    if not product:
        return jsonify({"error": "Product not found"}), 404
    if product.quantity < quantity:
        return jsonify({"error": "Insufficient stock for product"}), 400

    product.quantity -= quantity

    order = Order(
        product_id=product_id,
        quantity=quantity,
        total_price=product.price * quantity,
        status="confirmed",
    )

    db.session.add(order)
    db.session.commit()

    return jsonify(order.to_dict()), 201


@orders_bp.route("/orders", methods=["GET"])
def list_orders():
    orders = Order.query.all()
    return jsonify([o.to_dict() for o in orders])
