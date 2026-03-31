from flask import Blueprint, request, jsonify
from app import db
from app.models.product import Product
from app.models.order import Order

orders_bp = Blueprint("orders", __name__)


@orders_bp.route("/orders", methods=["POST"])
def create_order():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    missing = [f for f in ("product_id", "quantity") if f not in data]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

    product = Product.query.get(data["product_id"])
    if not product:
        return jsonify({"error": "Product not found"}), 404

    quantity = data["quantity"]
    if not isinstance(quantity, int) or quantity <= 0:
        return jsonify({"error": "quantity must be a positive integer"}), 400

    if product.quantity < quantity:
        return jsonify({"error": "Insufficient stock"}), 400

    product.quantity -= quantity

    order = Order(
        product_id=product.id,
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
