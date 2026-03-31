import pytest
from app import create_app, db


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


class TestProductEndpoints:
    def test_list_products_empty(self, client):
        response = client.get("/api/v1/products")
        assert response.status_code == 200
        assert response.get_json() == []

    def test_create_product(self, client):
        data = {
            "name": "Widget A",
            "sku": "WGT-001",
            "price": 29.99,
            "quantity": 100,
        }
        response = client.post("/api/v1/products", json=data)
        assert response.status_code == 201
        result = response.get_json()
        assert result["name"] == "Widget A"
        assert result["sku"] == "WGT-001"

    def test_create_product_missing_name(self, client):
        """Test product creation fails when name is missing"""
        data = {
            "sku": "WGT-002",
            "price": 29.99,
        }
        response = client.post("/api/v1/products", json=data)
        assert response.status_code == 400
        result = response.get_json()
        assert "name is required" in result["error"]

    def test_create_product_missing_sku(self, client):
        """Test product creation fails when sku is missing"""
        data = {
            "name": "Widget B",
            "price": 29.99,
        }
        response = client.post("/api/v1/products", json=data)
        assert response.status_code == 400
        result = response.get_json()
        assert "sku is required" in result["error"]

    def test_create_product_missing_price(self, client):
        """Test product creation fails when price is missing"""
        data = {
            "name": "Widget C",
            "sku": "WGT-003",
        }
        response = client.post("/api/v1/products", json=data)
        assert response.status_code == 400
        result = response.get_json()
        assert "price is required" in result["error"]

    def test_create_product_negative_price(self, client):
        """Test product creation fails with negative price"""
        data = {
            "name": "Widget D",
            "sku": "WGT-004",
            "price": -10.00,
        }
        response = client.post("/api/v1/products", json=data)
        assert response.status_code == 400
        result = response.get_json()
        assert "price must be greater than 0" in result["error"]

    def test_create_product_zero_price(self, client):
        """Test product creation fails with zero price"""
        data = {
            "name": "Widget E",
            "sku": "WGT-005",
            "price": 0,
        }
        response = client.post("/api/v1/products", json=data)
        assert response.status_code == 400
        result = response.get_json()
        assert "price must be greater than 0" in result["error"]

    def test_create_product_invalid_price(self, client):
        """Test product creation fails with invalid price"""
        data = {
            "name": "Widget F",
            "sku": "WGT-006",
            "price": "invalid",
        }
        response = client.post("/api/v1/products", json=data)
        assert response.status_code == 400
        result = response.get_json()
        assert "price must be a valid number" in result["error"]

    def test_create_product_negative_quantity(self, client):
        """Test product creation fails with negative quantity"""
        data = {
            "name": "Widget G",
            "sku": "WGT-007",
            "price": 29.99,
            "quantity": -5,
        }
        response = client.post("/api/v1/products", json=data)
        assert response.status_code == 400
        result = response.get_json()
        assert "quantity cannot be negative" in result["error"]

    def test_create_product_invalid_quantity(self, client):
        """Test product creation fails with invalid quantity"""
        data = {
            "name": "Widget H",
            "sku": "WGT-008",
            "price": 29.99,
            "quantity": "invalid",
        }
        response = client.post("/api/v1/products", json=data)
        assert response.status_code == 400
        result = response.get_json()
        assert "quantity must be a valid integer" in result["error"]

    def test_create_product_empty_body(self, client):
        """Test product creation fails with empty request body"""
        # When json=None, Flask returns 415 Unsupported Media Type
        response = client.post("/api/v1/products", json=None)
        assert response.status_code == 415

        # Test with empty JSON object instead
        response = client.post("/api/v1/products", json={})
        assert response.status_code == 400
        result = response.get_json()
        assert "name is required" in result["error"]

    def test_create_product_duplicate_sku(self, client):
        """Test product creation fails with duplicate SKU"""
        data = {
            "name": "Widget I",
            "sku": "WGT-009",
            "price": 29.99,
        }
        # Create first product
        response1 = client.post("/api/v1/products", json=data)
        assert response1.status_code == 201

        # Try to create another product with same SKU
        data2 = {
            "name": "Widget J",
            "sku": "WGT-009",  # Same SKU
            "price": 39.99,
        }
        response2 = client.post("/api/v1/products", json=data2)
        assert response2.status_code == 400
        result = response2.get_json()
        assert "already exists" in result["error"]

    def test_create_product_with_description(self, client):
        """Test product creation with optional description"""
        data = {
            "name": "Widget K",
            "sku": "WGT-010",
            "price": 29.99,
            "description": "A detailed description",
        }
        response = client.post("/api/v1/products", json=data)
        assert response.status_code == 201
        result = response.get_json()
        assert result["description"] == "A detailed description"

    def test_create_product_with_custom_threshold(self, client):
        """Test product creation with custom low stock threshold"""
        data = {
            "name": "Widget L",
            "sku": "WGT-011",
            "price": 29.99,
            "low_stock_threshold": 5,
        }
        response = client.post("/api/v1/products", json=data)
        assert response.status_code == 201
        result = response.get_json()
        assert result["low_stock_threshold"] == 5

