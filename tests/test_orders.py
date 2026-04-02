class TestOrderEndpoints:
    def _create_product(self, client, quantity=10, price=5.0):
        response = client.post(
            "/api/v1/products",
            json={
                "name": "Widget",
                "sku": f"WGT-{quantity}-{price}",
                "price": price,
                "quantity": quantity,
            },
        )
        assert response.status_code == 201
        return response.get_json()["id"]

    def test_create_order_rejects_negative_quantity(self, client):
        product_id = self._create_product(client, quantity=5)

        response = client.post(
            "/api/v1/orders", json={"product_id": product_id, "quantity": -1}
        )

        assert response.status_code == 400
        assert response.get_json()["error"] == "Quantity must be a positive integer"

        product_response = client.get(f"/api/v1/products/{product_id}")
        assert product_response.get_json()["quantity"] == 5

    def test_create_order_rejects_zero_quantity(self, client):
        product_id = self._create_product(client, quantity=5)

        response = client.post(
            "/api/v1/orders", json={"product_id": product_id, "quantity": 0}
        )

        assert response.status_code == 400
        assert response.get_json()["error"] == "Quantity must be a positive integer"

    def test_create_order_rejects_insufficient_stock(self, client):
        product_id = self._create_product(client, quantity=2)

        response = client.post(
            "/api/v1/orders", json={"product_id": product_id, "quantity": 3}
        )

        assert response.status_code == 400
        assert response.get_json()["error"] == "Insufficient stock for product"

        product_response = client.get(f"/api/v1/products/{product_id}")
        assert product_response.get_json()["quantity"] == 2

    def test_create_order_missing_fields(self, client):
        response = client.post("/api/v1/orders", json={})

        assert response.status_code == 400
        assert response.get_json()["error"].startswith("Missing required fields")

    def test_create_order_updates_stock(self, client):
        product_id = self._create_product(client, quantity=5, price=3.5)

        response = client.post(
            "/api/v1/orders", json={"product_id": product_id, "quantity": 3}
        )

        assert response.status_code == 201
        order = response.get_json()
        assert order["quantity"] == 3
        assert order["product_id"] == product_id

        product_response = client.get(f"/api/v1/products/{product_id}")
        assert product_response.get_json()["quantity"] == 2
