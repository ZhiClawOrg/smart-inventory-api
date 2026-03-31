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
# Order endpoints
# ---------------------------------------------------------------------------

class TestOrderEndpoints:

    # --- List orders ---

    def test_list_orders_empty(self, client):
        response = client.get("/api/v1/orders")
        assert response.status_code == 200
        assert response.get_json() == []

    def test_list_orders_with_data(self, client, sample_product):
        client.post(
            "/api/v1/orders",
            json={"product_id": sample_product["id"], "quantity": 2},
        )
        response = client.get("/api/v1/orders")
        assert response.status_code == 200
        body = response.get_json()
        assert len(body) == 1
        assert body[0]["product_id"] == sample_product["id"]
        assert body[0]["quantity"] == 2

    # --- Create order (valid) ---

    def test_create_order_valid(self, client, sample_product):
        product_id = sample_product["id"]
        original_qty = sample_product["quantity"]
        order_qty = 5
        response = client.post(
            "/api/v1/orders",
            json={"product_id": product_id, "quantity": order_qty},
        )
        assert response.status_code == 201
        body = response.get_json()
        assert body["product_id"] == product_id
        assert body["quantity"] == order_qty
        assert body["total_price"] == pytest.approx(sample_product["price"] * order_qty)
        assert "id" in body
        assert "created_at" in body
        # Confirm product stock was decremented
        product_resp = client.get(f"/api/v1/products/{product_id}")
        assert product_resp.status_code == 200
        assert product_resp.get_json()["quantity"] == original_qty - order_qty

    # --- Create order (stock errors) ---

    def test_create_order_insufficient_stock(self, client, sample_product):
        product_id = sample_product["id"]
        response = client.post("/api/v1/orders",
                               json={"product_id": product_id, "quantity": 9999})
        assert response.status_code == 400
        body = response.get_json()
        assert body == {"error": "Insufficient stock"}

    def test_create_order_exact_stock(self, client, sample_product):
        product_id = sample_product["id"]
        exact_qty = sample_product["quantity"]   # order exactly what's in stock
        response = client.post("/api/v1/orders",
                               json={"product_id": product_id, "quantity": exact_qty})
        assert response.status_code == 201
        body = response.get_json()
        assert body["quantity"] == exact_qty
        # Stock should now be zero
        product_resp = client.get(f"/api/v1/products/{product_id}")
        assert product_resp.get_json()["quantity"] == 0

    # --- Create order (not-found product) ---

    def test_create_order_invalid_product_id(self, client):
        response = client.post("/api/v1/orders",
                               json={"product_id": 99999, "quantity": 1})
        assert response.status_code == 404
        body = response.get_json()
        assert "error" in body

    # --- Create order (missing / invalid fields) ---

    def test_create_order_missing_product_id(self, client):
        response = client.post("/api/v1/orders", json={"quantity": 1})
        assert response.status_code == 400
        body = response.get_json()
        assert "error" in body
        assert "product_id" in body["error"]

    def test_create_order_missing_quantity(self, client, sample_product):
        response = client.post("/api/v1/orders",
                               json={"product_id": sample_product["id"]})
        assert response.status_code == 400
        body = response.get_json()
        assert "error" in body
        assert "quantity" in body["error"]

    def test_create_order_zero_quantity(self, client, sample_product):
        response = client.post("/api/v1/orders",
                               json={"product_id": sample_product["id"], "quantity": 0})
        assert response.status_code == 400
        body = response.get_json()
        assert "error" in body
        assert "quantity" in body["error"]

    def test_create_order_negative_quantity(self, client, sample_product):
        response = client.post("/api/v1/orders",
                               json={"product_id": sample_product["id"], "quantity": -3})
        assert response.status_code == 400
        body = response.get_json()
        assert "error" in body
        assert "quantity" in body["error"]

    def test_create_order_invalid_json(self, client):
        response = client.post(
            "/api/v1/orders",
            data="not-json",
            content_type="application/json",
        )
        # Flask 3.x may return HTML 400 before the route runs; the important
        # contract is that a 400 is returned for malformed JSON.
        assert response.status_code == 400
