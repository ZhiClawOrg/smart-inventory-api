from flask import Blueprint, request, jsonify
from app import db
from app.models.product import Product

products_bp = Blueprint("products", __name__)


@products_bp.route("/products", methods=["GET"])
def list_products():
    products = Product.query.all()
    return jsonify([p.to_dict() for p in products])


@products_bp.route("/products", methods=["POST"])
def create_product():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    missing = [f for f in ("name", "sku", "price") if f not in data]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

    if not isinstance(data["price"], (int, float)) or data["price"] < 0:
        return jsonify({"error": "price must be a non-negative number"}), 400

    quantity = data.get("quantity", 0)
    if not isinstance(quantity, int) or quantity < 0:
        return jsonify({"error": "quantity must be a non-negative integer"}), 400

    if Product.query.filter_by(sku=data["sku"]).first():
        return jsonify({"error": "A product with that SKU already exists"}), 400

    product = Product(
        name=data["name"],
        sku=data["sku"],
        price=data["price"],
        description=data.get("description", ""),
        quantity=quantity,
        low_stock_threshold=data.get("low_stock_threshold", 10),
    )

    db.session.add(product)
    db.session.commit()

    return jsonify(product.to_dict()), 201


@products_bp.route("/products/<int:product_id>", methods=["GET"])
def get_product(product_id):
    product = Product.query.get(product_id)
    if not product:
        return jsonify({"error": "Product not found"}), 404

    return jsonify(product.to_dict())


@products_bp.route("/products/<int:product_id>", methods=["PUT"])
def update_product(product_id):
    product = Product.query.get(product_id)
    if not product:
        return jsonify({"error": "Product not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    product.name = data.get("name", product.name)
    product.price = data.get("price", product.price)
    product.description = data.get("description", product.description)
    product.quantity = data.get("quantity", product.quantity)

    db.session.commit()
    return jsonify(product.to_dict())


@products_bp.route("/products/<int:product_id>", methods=["DELETE"])
def delete_product(product_id):
    product = Product.query.get(product_id)
    if not product:
        return jsonify({"error": "Product not found"}), 404

    db.session.delete(product)
    db.session.commit()

    return jsonify({"message": "Product deleted"}), 200


@products_bp.route("/inventory/low-stock", methods=["GET"])
def low_stock_alerts():
    products = Product.query.filter(Product.quantity < Product.low_stock_threshold).all()
    return jsonify([p.to_dict() for p in products])
