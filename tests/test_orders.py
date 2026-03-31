import pytest
from app import create_app, db
from app.models.product import Product
from app.models.order import Order


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
def sample_product(app):
    """Create a sample product for testing"""
    with app.app_context():
        product = Product(
            name="Test Widget",
            sku="TEST-001",
            price=29.99,
            quantity=50,
            description="A test product",
        )
        db.session.add(product)
        db.session.commit()
        return product.id


class TestOrderEndpoints:
    def test_create_order_success(self, client, sample_product):
        """Test successful order creation with sufficient stock"""
        data = {
            "product_id": sample_product,
            "quantity": 10,
        }
        response = client.post("/api/v1/orders", json=data)
        assert response.status_code == 201
        result = response.get_json()
        assert result["product_id"] == sample_product
        assert result["quantity"] == 10
        assert result["status"] == "confirmed"
        assert result["total_price"] == 29.99 * 10

    def test_create_order_insufficient_stock(self, client, sample_product):
        """Test order rejection when stock is insufficient"""
        data = {
            "product_id": sample_product,
            "quantity": 100,  # More than available (50)
        }
        response = client.post("/api/v1/orders", json=data)
        assert response.status_code == 400
        result = response.get_json()
        assert "Insufficient stock" in result["error"]
        assert result["available"] == 50
        assert result["requested"] == 100

    def test_create_order_negative_quantity(self, client, sample_product):
        """Test order rejection with negative quantity"""
        data = {
            "product_id": sample_product,
            "quantity": -5,
        }
        response = client.post("/api/v1/orders", json=data)
        assert response.status_code == 400
        result = response.get_json()
        assert "must be greater than 0" in result["error"]

    def test_create_order_zero_quantity(self, client, sample_product):
        """Test order rejection with zero quantity"""
        data = {
            "product_id": sample_product,
            "quantity": 0,
        }
        response = client.post("/api/v1/orders", json=data)
        assert response.status_code == 400
        result = response.get_json()
        assert "must be greater than 0" in result["error"]

    def test_create_order_missing_product_id(self, client):
        """Test order rejection when product_id is missing"""
        data = {
            "quantity": 5,
        }
        response = client.post("/api/v1/orders", json=data)
        assert response.status_code == 400
        result = response.get_json()
        assert "product_id is required" in result["error"]

    def test_create_order_missing_quantity(self, client, sample_product):
        """Test order rejection when quantity is missing"""
        data = {
            "product_id": sample_product,
        }
        response = client.post("/api/v1/orders", json=data)
        assert response.status_code == 400
        result = response.get_json()
        assert "quantity is required" in result["error"]

    def test_create_order_empty_body(self, client):
        """Test order rejection with empty request body"""
        # When json=None, Flask returns 415 Unsupported Media Type
        response = client.post("/api/v1/orders", json=None)
        assert response.status_code == 415

        # Test with empty JSON object instead
        response = client.post("/api/v1/orders", json={})
        assert response.status_code == 400
        result = response.get_json()
        assert "product_id is required" in result["error"]

    def test_create_order_invalid_product_id(self, client):
        """Test order rejection with invalid product_id"""
        data = {
            "product_id": "invalid",
            "quantity": 5,
        }
        response = client.post("/api/v1/orders", json=data)
        assert response.status_code == 400
        result = response.get_json()
        assert "must be valid integers" in result["error"]

    def test_create_order_invalid_quantity(self, client, sample_product):
        """Test order rejection with invalid quantity"""
        data = {
            "product_id": sample_product,
            "quantity": "invalid",
        }
        response = client.post("/api/v1/orders", json=data)
        assert response.status_code == 400
        result = response.get_json()
        assert "must be valid integers" in result["error"]

    def test_create_order_nonexistent_product(self, client):
        """Test order rejection when product doesn't exist"""
        data = {
            "product_id": 99999,
            "quantity": 5,
        }
        response = client.post("/api/v1/orders", json=data)
        assert response.status_code == 404
        result = response.get_json()
        assert "Product not found" in result["error"]

    def test_create_order_updates_stock(self, client, app, sample_product):
        """Test that creating an order decreases product stock"""
        data = {
            "product_id": sample_product,
            "quantity": 10,
        }
        response = client.post("/api/v1/orders", json=data)
        assert response.status_code == 201

        # Check that stock was reduced
        with app.app_context():
            product = Product.query.get(sample_product)
            assert product.quantity == 40  # 50 - 10

    def test_create_multiple_orders_stock_tracking(self, client, app, sample_product):
        """Test that multiple orders correctly update stock"""
        # First order
        data1 = {
            "product_id": sample_product,
            "quantity": 20,
        }
        response1 = client.post("/api/v1/orders", json=data1)
        assert response1.status_code == 201

        # Second order
        data2 = {
            "product_id": sample_product,
            "quantity": 15,
        }
        response2 = client.post("/api/v1/orders", json=data2)
        assert response2.status_code == 201

        # Check remaining stock
        with app.app_context():
            product = Product.query.get(sample_product)
            assert product.quantity == 15  # 50 - 20 - 15

        # Try to order more than remaining stock
        data3 = {
            "product_id": sample_product,
            "quantity": 20,
        }
        response3 = client.post("/api/v1/orders", json=data3)
        assert response3.status_code == 400
        result = response3.get_json()
        assert "Insufficient stock" in result["error"]

    def test_list_orders_empty(self, client):
        """Test listing orders when none exist"""
        response = client.get("/api/v1/orders")
        assert response.status_code == 200
        assert response.get_json() == []

    def test_list_orders(self, client, sample_product):
        """Test listing orders after creating some"""
        # Create first order
        data1 = {
            "product_id": sample_product,
            "quantity": 5,
        }
        client.post("/api/v1/orders", json=data1)

        # Create second order
        data2 = {
            "product_id": sample_product,
            "quantity": 10,
        }
        client.post("/api/v1/orders", json=data2)

        # List orders
        response = client.get("/api/v1/orders")
        assert response.status_code == 200
        orders = response.get_json()
        assert len(orders) == 2
        assert orders[0]["quantity"] == 5
        assert orders[1]["quantity"] == 10
