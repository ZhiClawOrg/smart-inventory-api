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

    # BUG: No input validation - missing required fields not checked
    product = Product(
        name=data["name"],
        sku=data["sku"],
        price=data["price"],
        description=data.get("description", ""),
        quantity=data.get("quantity", 0),
        low_stock_threshold=data.get("low_stock_threshold", 10),
    )

    db.session.add(product)
    db.session.commit()

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
