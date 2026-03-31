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

    # TODO: Add more tests for update, delete, error cases
