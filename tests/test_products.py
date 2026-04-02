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

    def test_create_product_missing_required_fields(self, client):
        response = client.post("/api/v1/products", json={"sku": "WGT-002"})
        assert response.status_code == 400
        assert response.get_json()["error"].startswith("Missing required fields")

    def test_get_product_not_found(self, client):
        response = client.get("/api/v1/products/99999")
        assert response.status_code == 404
        result = response.get_json()
        assert result["error"] == "Product not found"
        assert result["status"] == 404

    # TODO: Add more tests for update, delete, error cases
