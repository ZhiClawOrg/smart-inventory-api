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
    """Create and return a standard product for use across tests."""
    data = {
        "name": "Widget A",
        "sku": "WGT-001",
        "price": 29.99,
        "description": "A standard test widget",
        "quantity": 50,
        "low_stock_threshold": 10,
    }
    response = client.post("/api/v1/products", json=data)
    return response.get_json()


# ---------------------------------------------------------------------------
# GET /api/v1/products
# ---------------------------------------------------------------------------

class TestListProducts:
    def test_list_products_empty(self, client):
        """GET /products returns an empty list when no products exist."""
        # Arrange – DB is empty by fixture
        # Act
        response = client.get("/api/v1/products")
        # Assert
        assert response.status_code == 200
        assert response.get_json() == []

    def test_list_products_returns_200(self, client, sample_product):
        """GET /products returns HTTP 200 when products are present."""
        response = client.get("/api/v1/products")
        assert response.status_code == 200

    def test_list_products_with_single_product(self, client, sample_product):
        """GET /products returns a list containing the created product."""
        # Act
        response = client.get("/api/v1/products")
        data = response.get_json()
        # Assert
        assert len(data) == 1
        assert data[0]["name"] == "Widget A"
        assert data[0]["sku"] == "WGT-001"

    def test_list_products_contains_all_fields(self, client, sample_product):
        """GET /products response includes every field from to_dict()."""
        response = client.get("/api/v1/products")
        product = response.get_json()[0]

        expected_keys = {
            "id", "name", "sku", "description", "price",
            "quantity", "low_stock_threshold", "created_at", "updated_at",
        }
        assert expected_keys == set(product.keys())

    def test_list_products_with_multiple_products(self, client):
        """GET /products returns all products when multiple exist."""
        # Arrange
        skus = ["SKU-A", "SKU-B", "SKU-C"]
        for sku in skus:
            client.post("/api/v1/products", json={"name": "Product", "sku": sku, "price": 9.99})

        # Act
        response = client.get("/api/v1/products")
        data = response.get_json()

        # Assert
        assert len(data) == 3
        returned_skus = {p["sku"] for p in data}
        assert returned_skus == set(skus)

    def test_list_products_field_values_match_creation(self, client, sample_product):
        """GET /products field values exactly match those provided at creation."""
        response = client.get("/api/v1/products")
        product = response.get_json()[0]

        assert product["name"] == "Widget A"
        assert product["sku"] == "WGT-001"
        assert product["price"] == 29.99
        assert product["description"] == "A standard test widget"
        assert product["quantity"] == 50
        assert product["low_stock_threshold"] == 10


# ---------------------------------------------------------------------------
# POST /api/v1/products
# ---------------------------------------------------------------------------

class TestCreateProduct:
    def test_create_product_with_all_fields(self, client):
        """POST /products with all fields returns 201 and the new product."""
        # Arrange
        data = {
            "name": "Full Product",
            "sku": "FULL-001",
            "price": 49.99,
            "description": "Complete product",
            "quantity": 100,
            "low_stock_threshold": 20,
        }
        # Act
        response = client.post("/api/v1/products", json=data)
        result = response.get_json()

        # Assert
        assert response.status_code == 201
        assert result["name"] == "Full Product"
        assert result["sku"] == "FULL-001"
        assert result["price"] == 49.99
        assert result["description"] == "Complete product"
        assert result["quantity"] == 100
        assert result["low_stock_threshold"] == 20

    def test_create_product_with_required_fields_only(self, client):
        """POST /products with only required fields (name, sku, price) returns 201."""
        # Arrange
        data = {"name": "Minimal Product", "sku": "MIN-001", "price": 5.00}
        # Act
        response = client.post("/api/v1/products", json=data)
        # Assert
        assert response.status_code == 201
        result = response.get_json()
        assert result["name"] == "Minimal Product"
        assert result["sku"] == "MIN-001"
        assert result["price"] == 5.00

    def test_create_product_default_quantity_is_zero(self, client):
        """POST /products without quantity defaults to 0."""
        data = {"name": "No Qty", "sku": "NQ-001", "price": 1.00}
        response = client.post("/api/v1/products", json=data)
        assert response.get_json()["quantity"] == 0

    def test_create_product_default_low_stock_threshold_is_ten(self, client):
        """POST /products without low_stock_threshold defaults to 10."""
        data = {"name": "No Threshold", "sku": "NT-001", "price": 1.00}
        response = client.post("/api/v1/products", json=data)
        assert response.get_json()["low_stock_threshold"] == 10

    def test_create_product_returns_id(self, client):
        """POST /products response includes a generated integer id."""
        data = {"name": "Has ID", "sku": "ID-001", "price": 1.00}
        response = client.post("/api/v1/products", json=data)
        result = response.get_json()
        assert "id" in result
        assert isinstance(result["id"], int)

    def test_create_product_returns_timestamps(self, client):
        """POST /products response includes created_at and updated_at timestamps."""
        data = {"name": "Timestamped", "sku": "TS-001", "price": 1.00}
        response = client.post("/api/v1/products", json=data)
        result = response.get_json()
        assert "created_at" in result
        assert "updated_at" in result
        assert result["created_at"] is not None
        assert result["updated_at"] is not None

    def test_create_product_with_zero_price(self, client):
        """POST /products allows a price of 0."""
        data = {"name": "Free Item", "sku": "FREE-001", "price": 0.0}
        response = client.post("/api/v1/products", json=data)
        assert response.status_code == 201
        assert response.get_json()["price"] == 0.0

    def test_create_product_with_large_quantity(self, client):
        """POST /products accepts very large quantity values."""
        data = {"name": "Bulk Item", "sku": "BULK-001", "price": 1.00, "quantity": 1_000_000}
        response = client.post("/api/v1/products", json=data)
        assert response.status_code == 201
        assert response.get_json()["quantity"] == 1_000_000

    # --- Known-bug tests: missing required fields cause unhandled exceptions ---
    # Flask's TESTING=True mode propagates exceptions instead of returning a 500
    # response. In production the unhandled exception surfaces as HTTP 500.
    # These tests document the bug by asserting the exception that propagates.

    def test_create_product_missing_name_raises_key_error(self, client):
        """BUG: POST /products without 'name' raises KeyError (should return 400).

        In production the unhandled KeyError becomes a 500 response.
        """
        data = {"sku": "NO-NAME-001", "price": 9.99}
        with pytest.raises(KeyError):
            client.post("/api/v1/products", json=data)

    def test_create_product_missing_sku_raises_key_error(self, client):
        """BUG: POST /products without 'sku' raises KeyError (should return 400).

        In production the unhandled KeyError becomes a 500 response.
        """
        data = {"name": "No SKU", "price": 9.99}
        with pytest.raises(KeyError):
            client.post("/api/v1/products", json=data)

    def test_create_product_missing_price_raises_key_error(self, client):
        """BUG: POST /products without 'price' raises KeyError (should return 400).

        In production the unhandled KeyError becomes a 500 response.
        """
        data = {"name": "No Price", "sku": "NP-001"}
        with pytest.raises(KeyError):
            client.post("/api/v1/products", json=data)

    def test_create_product_duplicate_sku_raises_integrity_error(self, client):
        """BUG: POST /products with duplicate SKU raises IntegrityError (should return 400/409).

        In production the unhandled IntegrityError becomes a 500 response.
        """
        from sqlalchemy.exc import IntegrityError

        data = {"name": "Widget", "sku": "DUP-001", "price": 9.99}
        # First creation succeeds
        first_response = client.post("/api/v1/products", json=data)
        assert first_response.status_code == 201

        # BUG: second creation with the same SKU raises IntegrityError
        with pytest.raises(IntegrityError):
            client.post("/api/v1/products", json=data)

    def test_create_product_is_retrievable_afterward(self, client):
        """A product created via POST is immediately retrievable via GET."""
        data = {"name": "Persist Test", "sku": "PERS-001", "price": 7.50}
        created = client.post("/api/v1/products", json=data).get_json()

        response = client.get(f"/api/v1/products/{created['id']}")
        assert response.status_code == 200
        assert response.get_json()["sku"] == "PERS-001"


# ---------------------------------------------------------------------------
# GET /api/v1/products/<id>
# ---------------------------------------------------------------------------

class TestGetProduct:
    def test_get_product_found(self, client, sample_product):
        """GET /products/<id> returns 200 and the correct product."""
        product_id = sample_product["id"]
        response = client.get(f"/api/v1/products/{product_id}")
        assert response.status_code == 200

    def test_get_product_contains_all_fields(self, client, sample_product):
        """GET /products/<id> response contains every field from to_dict()."""
        product_id = sample_product["id"]
        response = client.get(f"/api/v1/products/{product_id}")
        result = response.get_json()

        expected_keys = {
            "id", "name", "sku", "description", "price",
            "quantity", "low_stock_threshold", "created_at", "updated_at",
        }
        assert expected_keys == set(result.keys())

    def test_get_product_field_values_are_correct(self, client, sample_product):
        """GET /products/<id> returns the exact field values used at creation."""
        product_id = sample_product["id"]
        response = client.get(f"/api/v1/products/{product_id}")
        result = response.get_json()

        assert result["id"] == product_id
        assert result["name"] == "Widget A"
        assert result["sku"] == "WGT-001"
        assert result["price"] == 29.99
        assert result["description"] == "A standard test widget"
        assert result["quantity"] == 50
        assert result["low_stock_threshold"] == 10

    def test_get_product_not_found_returns_404(self, client):
        """GET /products/<id> for a non-existent id returns 404."""
        response = client.get("/api/v1/products/99999")
        assert response.status_code == 404

    def test_get_product_not_found_error_body(self, client):
        """GET /products/<id> 404 response body contains error and status fields."""
        response = client.get("/api/v1/products/99999")
        result = response.get_json()
        assert result["error"] == "Product not found"
        assert result["status"] == 404

    def test_get_product_not_found_after_no_creation(self, client):
        """GET /products/1 returns 404 when the DB is completely empty."""
        response = client.get("/api/v1/products/1")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# PUT /api/v1/products/<id>
# ---------------------------------------------------------------------------

class TestUpdateProduct:
    def test_update_product_name(self, client, sample_product):
        """PUT /products/<id> can update the product name."""
        product_id = sample_product["id"]
        response = client.put(f"/api/v1/products/{product_id}", json={"name": "Updated Widget"})
        assert response.status_code == 200
        assert response.get_json()["name"] == "Updated Widget"

    def test_update_product_price(self, client, sample_product):
        """PUT /products/<id> can update the price."""
        product_id = sample_product["id"]
        response = client.put(f"/api/v1/products/{product_id}", json={"price": 99.99})
        assert response.status_code == 200
        assert response.get_json()["price"] == 99.99

    def test_update_product_quantity(self, client, sample_product):
        """PUT /products/<id> can update the quantity."""
        product_id = sample_product["id"]
        response = client.put(f"/api/v1/products/{product_id}", json={"quantity": 200})
        assert response.status_code == 200
        assert response.get_json()["quantity"] == 200

    def test_update_product_description(self, client, sample_product):
        """PUT /products/<id> can update the description."""
        product_id = sample_product["id"]
        response = client.put(f"/api/v1/products/{product_id}", json={"description": "New description"})
        assert response.status_code == 200
        assert response.get_json()["description"] == "New description"

    def test_update_product_all_fields_at_once(self, client, sample_product):
        """PUT /products/<id> can update name, price, quantity, and description together."""
        product_id = sample_product["id"]
        payload = {
            "name": "Completely Updated",
            "price": 199.99,
            "quantity": 5,
            "description": "Fully updated product",
        }
        response = client.put(f"/api/v1/products/{product_id}", json=payload)
        result = response.get_json()

        assert response.status_code == 200
        assert result["name"] == "Completely Updated"
        assert result["price"] == 199.99
        assert result["quantity"] == 5
        assert result["description"] == "Fully updated product"

    def test_update_product_partial_preserves_other_fields(self, client, sample_product):
        """PUT /products/<id> updating only name keeps other fields unchanged."""
        product_id = sample_product["id"]
        client.put(f"/api/v1/products/{product_id}", json={"name": "Partial Update"})

        # Verify unchanged fields
        response = client.get(f"/api/v1/products/{product_id}")
        result = response.get_json()
        assert result["sku"] == "WGT-001"        # sku is not updatable via this route
        assert result["price"] == 29.99          # price unchanged
        assert result["quantity"] == 50          # quantity unchanged

    def test_update_product_returns_updated_resource(self, client, sample_product):
        """PUT /products/<id> returns the full updated product dict."""
        product_id = sample_product["id"]
        response = client.put(f"/api/v1/products/{product_id}", json={"price": 55.55})
        result = response.get_json()

        expected_keys = {
            "id", "name", "sku", "description", "price",
            "quantity", "low_stock_threshold", "created_at", "updated_at",
        }
        assert expected_keys == set(result.keys())

    def test_update_product_not_found_returns_404(self, client):
        """PUT /products/<id> for non-existent id returns 404."""
        response = client.put("/api/v1/products/99999", json={"name": "Ghost"})
        assert response.status_code == 404

    def test_update_product_not_found_error_body(self, client):
        """PUT /products/<id> 404 response contains the expected error message."""
        response = client.put("/api/v1/products/99999", json={"name": "Ghost"})
        assert response.get_json()["error"] == "Product not found"

    def test_update_product_change_persists(self, client, sample_product):
        """A value updated via PUT is reflected in a subsequent GET."""
        product_id = sample_product["id"]
        client.put(f"/api/v1/products/{product_id}", json={"price": 77.77})

        response = client.get(f"/api/v1/products/{product_id}")
        assert response.get_json()["price"] == 77.77


# ---------------------------------------------------------------------------
# DELETE /api/v1/products/<id>
# ---------------------------------------------------------------------------

class TestDeleteProduct:
    def test_delete_product_returns_204(self, client, sample_product):
        """DELETE /products/<id> returns HTTP 204 for a valid product."""
        product_id = sample_product["id"]
        response = client.delete(f"/api/v1/products/{product_id}")
        assert response.status_code == 204

    def test_delete_product_returns_empty_body(self, client, sample_product):
        """DELETE /products/<id> returns an empty response body on success."""
        product_id = sample_product["id"]
        response = client.delete(f"/api/v1/products/{product_id}")
        assert response.data == b""

    def test_delete_product_not_found_returns_404(self, client):
        """DELETE /products/<id> for non-existent id returns 404."""
        response = client.delete("/api/v1/products/99999")
        assert response.status_code == 404

    def test_delete_product_not_found_error_body(self, client):
        """DELETE /products/<id> 404 response contains the expected error message."""
        response = client.delete("/api/v1/products/99999")
        assert response.get_json()["error"] == "Product not found"

    def test_delete_product_is_no_longer_retrievable(self, client, sample_product):
        """After DELETE, a GET for the same id returns 404."""
        product_id = sample_product["id"]
        client.delete(f"/api/v1/products/{product_id}")

        response = client.get(f"/api/v1/products/{product_id}")
        assert response.status_code == 404

    def test_delete_product_removed_from_list(self, client, sample_product):
        """After DELETE, the product no longer appears in GET /products."""
        product_id = sample_product["id"]
        client.delete(f"/api/v1/products/{product_id}")

        response = client.get("/api/v1/products")
        assert response.get_json() == []

    def test_delete_product_only_removes_target(self, client):
        """DELETE removes only the targeted product; others remain intact."""
        # Arrange – create two products
        r1 = client.post("/api/v1/products", json={"name": "Keep Me", "sku": "KEEP-001", "price": 1.00})
        r2 = client.post("/api/v1/products", json={"name": "Delete Me", "sku": "DEL-001", "price": 1.00})
        keep_id = r1.get_json()["id"]
        del_id = r2.get_json()["id"]

        # Act
        client.delete(f"/api/v1/products/{del_id}")

        # Assert
        assert client.get(f"/api/v1/products/{keep_id}").status_code == 200
        assert client.get(f"/api/v1/products/{del_id}").status_code == 404

    def test_delete_same_product_twice_returns_404_second_time(self, client, sample_product):
        """Deleting the same product twice: first 204, second 404."""
        product_id = sample_product["id"]
        first = client.delete(f"/api/v1/products/{product_id}")
        second = client.delete(f"/api/v1/products/{product_id}")
        assert first.status_code == 204
        assert second.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/v1/inventory/low-stock
# ---------------------------------------------------------------------------

class TestLowStockInventory:
    def test_low_stock_empty_when_no_products(self, client):
        """GET /inventory/low-stock returns [] when there are no products."""
        response = client.get("/api/v1/inventory/low-stock")
        assert response.status_code == 200
        assert response.get_json() == []

    def test_low_stock_empty_when_all_products_above_threshold(self, client):
        """GET /inventory/low-stock returns [] when all products have quantity >= 10."""
        client.post("/api/v1/products", json={"name": "Well Stocked", "sku": "WS-001", "price": 5.00, "quantity": 10})
        client.post("/api/v1/products", json={"name": "Also Fine", "sku": "WS-002", "price": 5.00, "quantity": 100})

        response = client.get("/api/v1/inventory/low-stock")
        assert response.get_json() == []

    def test_low_stock_returns_products_with_quantity_below_10(self, client):
        """GET /inventory/low-stock returns products whose quantity is < 10."""
        client.post("/api/v1/products", json={"name": "Low Stock Item", "sku": "LS-001", "price": 5.00, "quantity": 5})

        response = client.get("/api/v1/inventory/low-stock")
        data = response.get_json()

        assert len(data) == 1
        assert data[0]["sku"] == "LS-001"
        assert data[0]["quantity"] == 5

    def test_low_stock_does_not_include_quantity_exactly_10(self, client):
        """Boundary: quantity == 10 is NOT included in low-stock (threshold is strictly < 10)."""
        # BUG note: threshold is hardcoded to 10, not using product's low_stock_threshold field
        client.post("/api/v1/products", json={"name": "Boundary Item", "sku": "BND-010", "price": 1.00, "quantity": 10})

        response = client.get("/api/v1/inventory/low-stock")
        assert response.get_json() == []

    def test_low_stock_includes_quantity_exactly_9(self, client):
        """Boundary: quantity == 9 IS included in low-stock (9 < 10)."""
        client.post("/api/v1/products", json={"name": "Just Under", "sku": "BND-009", "price": 1.00, "quantity": 9})

        response = client.get("/api/v1/inventory/low-stock")
        data = response.get_json()
        assert len(data) == 1
        assert data[0]["quantity"] == 9

    def test_low_stock_includes_quantity_zero(self, client):
        """GET /inventory/low-stock includes products with quantity of 0."""
        client.post("/api/v1/products", json={"name": "Out of Stock", "sku": "OOS-001", "price": 1.00, "quantity": 0})

        response = client.get("/api/v1/inventory/low-stock")
        data = response.get_json()
        assert len(data) == 1
        assert data[0]["quantity"] == 0

    def test_low_stock_filters_correctly_with_mixed_quantities(self, client):
        """GET /inventory/low-stock returns only products below 10 in a mixed set."""
        # Arrange
        client.post("/api/v1/products", json={"name": "Below", "sku": "MIX-001", "price": 1.00, "quantity": 3})
        client.post("/api/v1/products", json={"name": "At boundary", "sku": "MIX-010", "price": 1.00, "quantity": 10})
        client.post("/api/v1/products", json={"name": "Above", "sku": "MIX-050", "price": 1.00, "quantity": 50})

        # Act
        response = client.get("/api/v1/inventory/low-stock")
        data = response.get_json()

        # Assert – only the item with quantity=3 should appear
        assert len(data) == 1
        assert data[0]["sku"] == "MIX-001"

    def test_low_stock_ignores_products_own_threshold_field(self, client):
        """BUG: threshold is hardcoded to 10; product's low_stock_threshold field is ignored.

        A product with quantity=15 and low_stock_threshold=20 should theoretically appear
        as low-stock (15 < 20), but the hardcoded check (< 10) means it does NOT.
        """
        # Arrange – product with a custom high threshold but quantity above 10
        client.post("/api/v1/products", json={
            "name": "Custom Threshold",
            "sku": "CT-001",
            "price": 1.00,
            "quantity": 15,
            "low_stock_threshold": 20,   # logically low-stock, but bug ignores this
        })

        # Act
        response = client.get("/api/v1/inventory/low-stock")

        # Assert – BUG: the product does NOT appear because 15 is not < 10
        assert response.get_json() == []

    def test_low_stock_multiple_low_items_all_returned(self, client):
        """GET /inventory/low-stock returns all products below the threshold."""
        for i in range(3):
            client.post("/api/v1/products", json={
                "name": f"Low {i}", "sku": f"LOW-00{i}", "price": 1.00, "quantity": i
            })

        response = client.get("/api/v1/inventory/low-stock")
        assert len(response.get_json()) == 3

    def test_low_stock_response_contains_all_product_fields(self, client):
        """GET /inventory/low-stock items include every field from to_dict()."""
        client.post("/api/v1/products", json={"name": "Field Check", "sku": "FC-001", "price": 2.00, "quantity": 1})
        response = client.get("/api/v1/inventory/low-stock")
        product = response.get_json()[0]

        expected_keys = {
            "id", "name", "sku", "description", "price",
            "quantity", "low_stock_threshold", "created_at", "updated_at",
        }
        assert expected_keys == set(product.keys())
