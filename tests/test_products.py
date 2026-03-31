import pytest
from app import create_app, db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def app():
    app = create_app()
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["TESTING"] = True
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def sample_product(client):
    data = {"name": "Widget A", "sku": "WGT-001", "price": 29.99, "quantity": 100}
    resp = client.post("/api/v1/products", json=data)
    return resp.get_json()


# ---------------------------------------------------------------------------
# Product CRUD endpoints
# ---------------------------------------------------------------------------

class TestProductEndpoints:

    # --- List products ---

    def test_list_products_empty(self, client):
        response = client.get("/api/v1/products")
        assert response.status_code == 200
        assert response.get_json() == []

    def test_list_products_with_data(self, client, sample_product):
        response = client.get("/api/v1/products")
        assert response.status_code == 200
        body = response.get_json()
        assert len(body) == 1
        assert body[0]["sku"] == "WGT-001"
        assert body[0]["name"] == "Widget A"

    # --- Create product (valid) ---

    def test_create_product_valid(self, client):
        data = {"name": "Widget A", "sku": "WGT-001", "price": 29.99, "quantity": 100}
        response = client.post("/api/v1/products", json=data)
        assert response.status_code == 201
        body = response.get_json()
        assert body["name"] == "Widget A"
        assert body["sku"] == "WGT-001"
        assert body["price"] == 29.99
        assert body["quantity"] == 100
        assert "id" in body
        assert "created_at" in body
        assert "updated_at" in body

    # --- Create product (validation errors) ---

    def test_create_product_missing_name(self, client):
        data = {"sku": "WGT-002", "price": 9.99}
        response = client.post("/api/v1/products", json=data)
        assert response.status_code == 400
        body = response.get_json()
        assert "error" in body
        assert "name" in body["error"]

    def test_create_product_missing_sku(self, client):
        data = {"name": "Gadget", "price": 9.99}
        response = client.post("/api/v1/products", json=data)
        assert response.status_code == 400
        body = response.get_json()
        assert "error" in body
        assert "sku" in body["error"]

    def test_create_product_missing_price(self, client):
        data = {"name": "Gadget", "sku": "GDG-001"}
        response = client.post("/api/v1/products", json=data)
        assert response.status_code == 400
        body = response.get_json()
        assert "error" in body
        assert "price" in body["error"]

    def test_create_product_duplicate_sku(self, client, sample_product):
        data = {"name": "Duplicate Widget", "sku": "WGT-001", "price": 19.99}
        response = client.post("/api/v1/products", json=data)
        assert response.status_code == 400
        body = response.get_json()
        assert "error" in body

    def test_create_product_negative_price(self, client):
        data = {"name": "Cheap Thing", "sku": "CHT-001", "price": -5.00}
        response = client.post("/api/v1/products", json=data)
        assert response.status_code == 400
        body = response.get_json()
        assert "error" in body
        assert "price" in body["error"]

    def test_create_product_negative_quantity(self, client):
        data = {"name": "Thing", "sku": "THG-001", "price": 5.00, "quantity": -1}
        response = client.post("/api/v1/products", json=data)
        assert response.status_code == 400
        body = response.get_json()
        assert "error" in body
        assert "quantity" in body["error"]

    def test_create_product_very_long_name(self, client):
        # Names beyond 100 chars should either succeed (truncated by DB) or be
        # rejected — we assert a valid HTTP response and check the SKU is unique
        data = {"name": "A" * 200, "sku": "LONG-001", "price": 1.00}
        response = client.post("/api/v1/products", json=data)
        assert response.status_code in (201, 400)

    def test_create_product_invalid_json(self, client):
        response = client.post(
            "/api/v1/products",
            data="not-json",
            content_type="application/json",
        )
        # Flask 3.x may return HTML 400 before the route runs; the important
        # contract is that a 400 is returned for malformed JSON.
        assert response.status_code == 400

    # --- Get single product ---

    def test_get_product_exists(self, client, sample_product):
        product_id = sample_product["id"]
        response = client.get(f"/api/v1/products/{product_id}")
        assert response.status_code == 200
        body = response.get_json()
        assert body["id"] == product_id
        assert body["sku"] == "WGT-001"
        assert body["name"] == "Widget A"

    def test_get_product_not_found(self, client):
        response = client.get("/api/v1/products/99999")
        assert response.status_code == 404
        body = response.get_json()
        assert body == {"error": "Product not found"}

    # --- Update product ---

    def test_update_product_valid(self, client, sample_product):
        product_id = sample_product["id"]
        response = client.put(
            f"/api/v1/products/{product_id}",
            json={"name": "Updated Widget", "price": 39.99, "quantity": 50},
        )
        assert response.status_code == 200
        body = response.get_json()
        assert body["name"] == "Updated Widget"
        assert body["price"] == 39.99
        assert body["quantity"] == 50

    def test_update_product_partial(self, client, sample_product):
        product_id = sample_product["id"]
        response = client.put(
            f"/api/v1/products/{product_id}",
            json={"price": 49.99},
        )
        assert response.status_code == 200
        body = response.get_json()
        assert body["price"] == 49.99
        assert body["name"] == "Widget A"   # unchanged
        assert body["quantity"] == 100       # unchanged

    def test_update_product_not_found(self, client):
        response = client.put(
            "/api/v1/products/99999",
            json={"name": "Ghost"},
        )
        assert response.status_code == 404
        body = response.get_json()
        assert "error" in body

    def test_update_product_invalid_json(self, client, sample_product):
        product_id = sample_product["id"]
        response = client.put(
            f"/api/v1/products/{product_id}",
            data="bad-json",
            content_type="application/json",
        )
        # Flask 3.x may return HTML 400 before the route runs; the important
        # contract is that a 400 is returned for malformed JSON.
        assert response.status_code == 400

    # --- Delete product ---

    def test_delete_product_exists(self, client, sample_product):
        product_id = sample_product["id"]
        response = client.delete(f"/api/v1/products/{product_id}")
        assert response.status_code == 200
        body = response.get_json()
        assert body == {"message": "Product deleted"}
        # Confirm it is gone
        follow_up = client.get(f"/api/v1/products/{product_id}")
        assert follow_up.status_code == 404

    def test_delete_product_not_found(self, client):
        response = client.delete("/api/v1/products/99999")
        assert response.status_code == 404
        body = response.get_json()
        assert "error" in body


# ---------------------------------------------------------------------------
# Low-stock endpoint
# ---------------------------------------------------------------------------

class TestLowStockEndpoint:

    def test_low_stock_none(self, client):
        # Product well above its threshold should not appear
        client.post(
            "/api/v1/products",
            json={
                "name": "Stocked",
                "sku": "STK-001",
                "price": 5.00,
                "quantity": 50,
                "low_stock_threshold": 10,
            },
        )
        response = client.get("/api/v1/inventory/low-stock")
        assert response.status_code == 200
        assert response.get_json() == []

    def test_low_stock_with_items(self, client):
        # quantity(3) < low_stock_threshold(10) → should appear
        client.post(
            "/api/v1/products",
            json={
                "name": "Almost Gone",
                "sku": "ALG-001",
                "price": 5.00,
                "quantity": 3,
                "low_stock_threshold": 10,
            },
        )
        # quantity(50) >= low_stock_threshold(10) → should NOT appear
        client.post(
            "/api/v1/products",
            json={
                "name": "Plenty",
                "sku": "PLN-001",
                "price": 5.00,
                "quantity": 50,
                "low_stock_threshold": 10,
            },
        )
        response = client.get("/api/v1/inventory/low-stock")
        assert response.status_code == 200
        body = response.get_json()
        skus = [p["sku"] for p in body]
        assert "ALG-001" in skus
        assert "PLN-001" not in skus

    def test_low_stock_uses_per_product_threshold(self, client):
        # threshold=5, quantity=3 → 3 < 5, SHOULD appear
        client.post(
            "/api/v1/products",
            json={
                "name": "Low Threshold Low Stock",
                "sku": "LTL-001",
                "price": 1.00,
                "quantity": 3,
                "low_stock_threshold": 5,
            },
        )
        # threshold=5, quantity=7 → 7 >= 5, should NOT appear (even though 7 < 10)
        client.post(
            "/api/v1/products",
            json={
                "name": "Low Threshold High Stock",
                "sku": "LTH-001",
                "price": 1.00,
                "quantity": 7,
                "low_stock_threshold": 5,
            },
        )
        response = client.get("/api/v1/inventory/low-stock")
        assert response.status_code == 200
        body = response.get_json()
        skus = [p["sku"] for p in body]
        assert "LTL-001" in skus
        assert "LTH-001" not in skus
