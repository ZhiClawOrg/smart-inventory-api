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
    """Create and return a product suitable for order tests."""
    data = {
        "name": "Orderable Widget",
        "sku": "ORD-001",
        "price": 25.00,
        "quantity": 100,
        "low_stock_threshold": 10,
    }
    response = client.post("/api/v1/products", json=data)
    assert response.status_code == 201
    return response.get_json()


def place_order(client, product_id, quantity):
    """Helper: POST a single order and return the response."""
    return client.post("/api/v1/orders", json={"product_id": product_id, "quantity": quantity})


# ---------------------------------------------------------------------------
# GET /api/v1/orders
# ---------------------------------------------------------------------------

class TestListOrders:
    def test_list_orders_empty(self, client):
        """GET /orders returns an empty list when no orders have been placed."""
        response = client.get("/api/v1/orders")
        assert response.status_code == 200
        assert response.get_json() == []

    def test_list_orders_returns_200(self, client, sample_product):
        """GET /orders returns HTTP 200 when orders are present."""
        place_order(client, sample_product["id"], 1)
        response = client.get("/api/v1/orders")
        assert response.status_code == 200

    def test_list_orders_with_single_order(self, client, sample_product):
        """GET /orders returns a list with one order after a single POST."""
        place_order(client, sample_product["id"], 2)

        response = client.get("/api/v1/orders")
        data = response.get_json()
        assert len(data) == 1

    def test_list_orders_contains_all_fields(self, client, sample_product):
        """GET /orders items contain every field from Order.to_dict()."""
        place_order(client, sample_product["id"], 1)

        response = client.get("/api/v1/orders")
        order = response.get_json()[0]

        expected_keys = {"id", "product_id", "quantity", "total_price", "status", "created_at"}
        assert expected_keys == set(order.keys())

    def test_list_orders_field_values_are_correct(self, client, sample_product):
        """GET /orders field values match the data used to create the order."""
        place_order(client, sample_product["id"], 3)

        order = client.get("/api/v1/orders").get_json()[0]

        assert order["product_id"] == sample_product["id"]
        assert order["quantity"] == 3
        assert order["total_price"] == 75.00   # 25.00 * 3
        assert order["status"] == "confirmed"

    def test_list_orders_with_multiple_orders(self, client, sample_product):
        """GET /orders returns all orders when several have been placed."""
        for qty in [1, 2, 3]:
            place_order(client, sample_product["id"], qty)

        response = client.get("/api/v1/orders")
        assert len(response.get_json()) == 3

    def test_list_orders_includes_created_at_timestamp(self, client, sample_product):
        """GET /orders order objects contain a non-null created_at timestamp."""
        place_order(client, sample_product["id"], 1)

        order = client.get("/api/v1/orders").get_json()[0]
        assert order["created_at"] is not None


# ---------------------------------------------------------------------------
# POST /api/v1/orders
# ---------------------------------------------------------------------------

class TestCreateOrder:
    def test_create_order_returns_201(self, client, sample_product):
        """POST /orders returns HTTP 201 on successful creation."""
        response = place_order(client, sample_product["id"], 1)
        assert response.status_code == 201

    def test_create_order_response_contains_all_fields(self, client, sample_product):
        """POST /orders response body contains every field from Order.to_dict()."""
        response = place_order(client, sample_product["id"], 1)
        result = response.get_json()

        expected_keys = {"id", "product_id", "quantity", "total_price", "status", "created_at"}
        assert expected_keys == set(result.keys())

    def test_create_order_status_is_confirmed(self, client, sample_product):
        """POST /orders sets order status to 'confirmed'."""
        response = place_order(client, sample_product["id"], 5)
        assert response.get_json()["status"] == "confirmed"

    def test_create_order_total_price_calculation(self, client, sample_product):
        """POST /orders calculates total_price as product.price * quantity."""
        # price=25.00, quantity=4 → total_price=100.00
        response = place_order(client, sample_product["id"], 4)
        assert response.get_json()["total_price"] == 100.00

    def test_create_order_total_price_with_decimal_price(self, client):
        """POST /orders correctly calculates total_price for a non-integer price."""
        # Arrange – product with a decimal price
        product = client.post(
            "/api/v1/products",
            json={"name": "Decimal Price", "sku": "DEC-001", "price": 9.99, "quantity": 50},
        ).get_json()

        # Act
        response = place_order(client, product["id"], 3)

        # Assert – 9.99 * 3 = 29.97
        total = response.get_json()["total_price"]
        assert round(total, 2) == 29.97

    def test_create_order_product_id_matches(self, client, sample_product):
        """POST /orders response product_id matches the requested product."""
        response = place_order(client, sample_product["id"], 1)
        assert response.get_json()["product_id"] == sample_product["id"]

    def test_create_order_quantity_matches(self, client, sample_product):
        """POST /orders response quantity matches the requested quantity."""
        response = place_order(client, sample_product["id"], 7)
        assert response.get_json()["quantity"] == 7

    def test_create_order_returns_generated_id(self, client, sample_product):
        """POST /orders response includes a generated integer id."""
        result = place_order(client, sample_product["id"], 1).get_json()
        assert "id" in result
        assert isinstance(result["id"], int)

    def test_create_order_decrements_product_quantity(self, client, sample_product):
        """POST /orders reduces the product's quantity by the ordered amount."""
        initial_qty = sample_product["quantity"]   # 100
        order_qty = 10

        place_order(client, sample_product["id"], order_qty)

        product = client.get(f"/api/v1/products/{sample_product['id']}").get_json()
        assert product["quantity"] == initial_qty - order_qty

    def test_create_order_stock_decrement_verified_via_get(self, client, sample_product):
        """Stock reduction from POST /orders is reflected in GET /products/<id>."""
        place_order(client, sample_product["id"], 30)

        product = client.get(f"/api/v1/products/{sample_product['id']}").get_json()
        assert product["quantity"] == 70  # 100 - 30

    def test_create_order_multiple_orders_cumulatively_reduce_stock(self, client, sample_product):
        """Multiple POST /orders calls reduce product stock cumulatively."""
        place_order(client, sample_product["id"], 20)
        place_order(client, sample_product["id"], 15)

        product = client.get(f"/api/v1/products/{sample_product['id']}").get_json()
        assert product["quantity"] == 65  # 100 - 20 - 15

    def test_create_order_with_quantity_of_one(self, client, sample_product):
        """POST /orders with quantity=1 decrements stock by exactly 1."""
        place_order(client, sample_product["id"], 1)
        product = client.get(f"/api/v1/products/{sample_product['id']}").get_json()
        assert product["quantity"] == 99

    def test_create_order_product_not_found_returns_404(self, client):
        """POST /orders with a non-existent product_id returns 404."""
        response = place_order(client, 99999, 1)
        assert response.status_code == 404

    def test_create_order_product_not_found_error_body(self, client):
        """POST /orders 404 response body contains the expected error message."""
        response = place_order(client, 99999, 1)
        assert response.get_json()["error"] == "Product not found"

    def test_create_order_quantity_exceeds_stock_is_allowed(self, client, sample_product):
        """BUG: POST /orders does NOT validate available stock.

        Ordering more than the available quantity is currently accepted (201),
        resulting in a negative product quantity. This is a known bug – the API
        should return 400 or 409 when quantity > stock.
        """
        # Arrange – initial stock is 100
        excess_qty = 150

        # Act – order more than available
        response = place_order(client, sample_product["id"], excess_qty)

        # BUG: no stock check → 201 accepted
        assert response.status_code == 201

        # BUG: product quantity goes negative
        product = client.get(f"/api/v1/products/{sample_product['id']}").get_json()
        assert product["quantity"] == -50  # 100 - 150

    def test_create_order_with_zero_initial_stock_still_accepted(self, client):
        """BUG: POST /orders with quantity > 0 when stock == 0 is accepted (negative stock)."""
        # Arrange – create a product with zero stock
        product = client.post(
            "/api/v1/products",
            json={"name": "Zero Stock", "sku": "ZS-001", "price": 10.00, "quantity": 0},
        ).get_json()

        # Act
        response = place_order(client, product["id"], 5)

        # BUG: accepted even though stock is 0
        assert response.status_code == 201

        # Product quantity is now negative
        updated = client.get(f"/api/v1/products/{product['id']}").get_json()
        assert updated["quantity"] == -5

    def test_create_order_appears_in_list_after_creation(self, client, sample_product):
        """An order placed via POST /orders is immediately retrievable via GET /orders."""
        created = place_order(client, sample_product["id"], 2).get_json()

        orders = client.get("/api/v1/orders").get_json()
        order_ids = [o["id"] for o in orders]
        assert created["id"] in order_ids

    def test_create_multiple_orders_each_has_unique_id(self, client, sample_product):
        """Each order created by POST /orders has a unique id."""
        ids = [
            place_order(client, sample_product["id"], i + 1).get_json()["id"]
            for i in range(3)
        ]
        assert len(set(ids)) == 3

    def test_create_order_for_product_with_exact_stock_match(self, client):
        """POST /orders with quantity == available stock empties stock to exactly 0."""
        product = client.post(
            "/api/v1/products",
            json={"name": "Exact Match", "sku": "EM-001", "price": 5.00, "quantity": 20},
        ).get_json()

        response = place_order(client, product["id"], 20)
        assert response.status_code == 201

        updated = client.get(f"/api/v1/products/{product['id']}").get_json()
        assert updated["quantity"] == 0
