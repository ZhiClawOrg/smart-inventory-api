from flask import Blueprint, request, jsonify
from app import db
from app.models.product import Product
from app.models.order import Order

orders_bp = Blueprint("orders", __name__)


@orders_bp.route("/orders", methods=["POST"])
def create_order():
    data = request.get_json()

    # Validate request body exists
    if data is None:
        return jsonify({"error": "Request body is required"}), 400

    # Validate required fields
    if "product_id" not in data:
        return jsonify({"error": "product_id is required"}), 400

    if "quantity" not in data:
        return jsonify({"error": "quantity is required"}), 400

    # Validate data types
    try:
        product_id = int(data["product_id"])
        quantity = int(data["quantity"])
    except (ValueError, TypeError):
        return jsonify({"error": "product_id and quantity must be valid integers"}), 400

    # Validate quantity is positive
    if quantity <= 0:
        return jsonify({"error": "quantity must be greater than 0"}), 400

    # Check if product exists
    product = Product.query.get(product_id)
    if not product:
        return jsonify({"error": "Product not found"}), 404

    # Validate sufficient stock is available
    if product.quantity < quantity:
        return jsonify({
            "error": "Insufficient stock",
            "available": product.quantity,
            "requested": quantity
        }), 400

    # Update stock and create order
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
