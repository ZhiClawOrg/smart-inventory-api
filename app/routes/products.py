from flask import Blueprint, request, jsonify
from app import db
from app.models.product import Product

products_bp = Blueprint("products", __name__)


@products_bp.route("/products", methods=["GET"])
def list_products():
    # Get query parameters
    search = request.args.get("search", "")
    min_price = request.args.get("min_price", type=float)
    max_price = request.args.get("max_price", type=float)
    in_stock = request.args.get("in_stock", "").lower() == "true"
    sort_by = request.args.get("sort_by", "id")
    order = request.args.get("order", "asc").lower()
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    # Validate sort field
    valid_sort_fields = ["name", "price", "quantity", "created_at", "id"]
    if sort_by not in valid_sort_fields:
        return jsonify({"error": f"Invalid sort_by field. Must be one of: {', '.join(valid_sort_fields)}"}), 400

    # Validate order
    if order not in ["asc", "desc"]:
        return jsonify({"error": "Invalid order. Must be 'asc' or 'desc'"}), 400

    # Validate pagination
    if page < 1:
        return jsonify({"error": "Page must be >= 1"}), 400
    if per_page < 1 or per_page > 100:
        return jsonify({"error": "per_page must be between 1 and 100"}), 400

    # Build query
    query = Product.query

    # Apply search filter (case-insensitive)
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            db.or_(
                Product.name.ilike(search_pattern),
                Product.description.ilike(search_pattern)
            )
        )

    # Apply price range filters
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)

    # Apply in-stock filter
    if in_stock:
        query = query.filter(Product.quantity > 0)

    # Apply sorting
    sort_column = getattr(Product, sort_by)
    if order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Get total count before pagination
    total = query.count()

    # Apply pagination
    offset = (page - 1) * per_page
    products = query.limit(per_page).offset(offset).all()

    # Calculate pagination info
    total_pages = (total + per_page - 1) // per_page if total > 0 else 0

    return jsonify({
        "products": [p.to_dict() for p in products],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    })


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
        return jsonify({"error": "Product not found", "status": 404}), 404

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
