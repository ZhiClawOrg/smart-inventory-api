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

    # Validate request body exists
    if data is None:
        return jsonify({"error": "Request body is required"}), 400

    # Validate required fields
    if "name" not in data:
        return jsonify({"error": "name is required"}), 400

    if "sku" not in data:
        return jsonify({"error": "sku is required"}), 400

    if "price" not in data:
        return jsonify({"error": "price is required"}), 400

    # Validate data types and values
    try:
        price = float(data["price"])
    except (ValueError, TypeError):
        return jsonify({"error": "price must be a valid number"}), 400

    if price <= 0:
        return jsonify({"error": "price must be greater than 0"}), 400

    # Validate quantity if provided
    quantity = data.get("quantity", 0)
    try:
        quantity = int(quantity)
    except (ValueError, TypeError):
        return jsonify({"error": "quantity must be a valid integer"}), 400

    if quantity < 0:
        return jsonify({"error": "quantity cannot be negative"}), 400

    # Validate low_stock_threshold if provided
    low_stock_threshold = data.get("low_stock_threshold", 10)
    try:
        low_stock_threshold = int(low_stock_threshold)
    except (ValueError, TypeError):
        return jsonify({"error": "low_stock_threshold must be a valid integer"}), 400

    if low_stock_threshold < 0:
        return jsonify({"error": "low_stock_threshold cannot be negative"}), 400

    product = Product(
        name=data["name"],
        sku=data["sku"],
        price=price,
        description=data.get("description", ""),
        quantity=quantity,
        low_stock_threshold=low_stock_threshold,
    )

    db.session.add(product)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        # Check if it's a duplicate SKU error
        if "UNIQUE constraint failed" in str(e) or "unique constraint" in str(e).lower():
            return jsonify({"error": "Product with this SKU already exists"}), 400
        return jsonify({"error": "Failed to create product"}), 500

    return jsonify(product.to_dict()), 201


@products_bp.route("/products/<int:product_id>", methods=["GET"])
def get_product(product_id):
    product = Product.query.get(product_id)
    if not product:
        # BUG: Returns 200 with None instead of proper 404
        return jsonify({"error": "not found"}), 200

    return jsonify(product.to_dict())


@products_bp.route("/products/<int:product_id>", methods=["PUT"])
def update_product(product_id):
    product = Product.query.get(product_id)
    if not product:
        return jsonify({"error": "Product not found"}), 404

    data = request.get_json()
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

    # BUG: No response body on successful delete
    return "", 204


@products_bp.route("/inventory/low-stock", methods=["GET"])
def low_stock_alerts():
    # BUG: Hardcoded threshold instead of using product's own threshold
    products = Product.query.filter(Product.quantity < 10).all()
    return jsonify([p.to_dict() for p in products])
