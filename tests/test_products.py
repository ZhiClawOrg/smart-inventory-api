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
        result = response.get_json()
        assert result["products"] == []
        assert result["pagination"]["total"] == 0

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

    def test_get_product_not_found(self, client):
        response = client.get("/api/v1/products/99999")
        assert response.status_code == 404
        result = response.get_json()
        assert result["error"] == "Product not found"
        assert result["status"] == 404

    # TODO: Add more tests for update, delete, error cases


class TestProductSearchAndFiltering:
    @pytest.fixture
    def sample_products(self, client):
        """Create sample products for testing"""
        products = [
            {"name": "Widget A", "sku": "WGT-001", "description": "A basic widget", "price": 10.99, "quantity": 5},
            {"name": "Widget B", "sku": "WGT-002", "description": "An advanced widget", "price": 25.99, "quantity": 0},
            {"name": "Gadget X", "sku": "GDG-001", "description": "A premium gadget", "price": 99.99, "quantity": 10},
            {"name": "Gadget Y", "sku": "GDG-002", "description": "A budget gadget", "price": 15.00, "quantity": 20},
            {"name": "Tool Z", "sku": "TOL-001", "description": "Essential tool", "price": 49.99, "quantity": 0},
        ]
        for product in products:
            client.post("/api/v1/products", json=product)
        return products

    def test_list_products_default_pagination(self, client, sample_products):
        """Test default pagination returns all products"""
        response = client.get("/api/v1/products")
        assert response.status_code == 200
        result = response.get_json()
        assert len(result["products"]) == 5
        assert result["pagination"]["page"] == 1
        assert result["pagination"]["per_page"] == 20
        assert result["pagination"]["total"] == 5
        assert result["pagination"]["total_pages"] == 1

    def test_search_by_name(self, client, sample_products):
        """Test search by product name (case-insensitive)"""
        response = client.get("/api/v1/products?search=widget")
        assert response.status_code == 200
        result = response.get_json()
        assert len(result["products"]) == 2
        assert all("widget" in p["name"].lower() for p in result["products"])

    def test_search_by_description(self, client, sample_products):
        """Test search by product description"""
        response = client.get("/api/v1/products?search=gadget")
        assert response.status_code == 200
        result = response.get_json()
        assert len(result["products"]) == 2
        assert all("gadget" in (p["name"].lower() + p["description"].lower()) for p in result["products"])

    def test_search_case_insensitive(self, client, sample_products):
        """Test that search is case-insensitive"""
        response1 = client.get("/api/v1/products?search=WIDGET")
        response2 = client.get("/api/v1/products?search=widget")
        assert response1.get_json() == response2.get_json()

    def test_filter_by_min_price(self, client, sample_products):
        """Test filtering by minimum price"""
        response = client.get("/api/v1/products?min_price=20")
        assert response.status_code == 200
        result = response.get_json()
        assert len(result["products"]) == 3
        assert all(p["price"] >= 20 for p in result["products"])

    def test_filter_by_max_price(self, client, sample_products):
        """Test filtering by maximum price"""
        response = client.get("/api/v1/products?max_price=20")
        assert response.status_code == 200
        result = response.get_json()
        assert len(result["products"]) == 2
        assert all(p["price"] <= 20 for p in result["products"])

    def test_filter_by_price_range(self, client, sample_products):
        """Test filtering by price range"""
        response = client.get("/api/v1/products?min_price=15&max_price=50")
        assert response.status_code == 200
        result = response.get_json()
        assert len(result["products"]) == 3
        assert all(15 <= p["price"] <= 50 for p in result["products"])

    def test_filter_in_stock_only(self, client, sample_products):
        """Test filtering for in-stock products only"""
        response = client.get("/api/v1/products?in_stock=true")
        assert response.status_code == 200
        result = response.get_json()
        assert len(result["products"]) == 3
        assert all(p["quantity"] > 0 for p in result["products"])

    def test_sort_by_price_asc(self, client, sample_products):
        """Test sorting by price ascending"""
        response = client.get("/api/v1/products?sort_by=price&order=asc")
        assert response.status_code == 200
        result = response.get_json()
        prices = [p["price"] for p in result["products"]]
        assert prices == sorted(prices)

    def test_sort_by_price_desc(self, client, sample_products):
        """Test sorting by price descending"""
        response = client.get("/api/v1/products?sort_by=price&order=desc")
        assert response.status_code == 200
        result = response.get_json()
        prices = [p["price"] for p in result["products"]]
        assert prices == sorted(prices, reverse=True)

    def test_sort_by_name(self, client, sample_products):
        """Test sorting by name"""
        response = client.get("/api/v1/products?sort_by=name&order=asc")
        assert response.status_code == 200
        result = response.get_json()
        names = [p["name"] for p in result["products"]]
        assert names == sorted(names)

    def test_sort_by_quantity(self, client, sample_products):
        """Test sorting by quantity"""
        response = client.get("/api/v1/products?sort_by=quantity&order=desc")
        assert response.status_code == 200
        result = response.get_json()
        quantities = [p["quantity"] for p in result["products"]]
        assert quantities == sorted(quantities, reverse=True)

    def test_pagination_page_1(self, client, sample_products):
        """Test pagination - first page"""
        response = client.get("/api/v1/products?page=1&per_page=2")
        assert response.status_code == 200
        result = response.get_json()
        assert len(result["products"]) == 2
        assert result["pagination"]["page"] == 1
        assert result["pagination"]["per_page"] == 2
        assert result["pagination"]["total"] == 5
        assert result["pagination"]["total_pages"] == 3
        assert result["pagination"]["has_next"] is True
        assert result["pagination"]["has_prev"] is False

    def test_pagination_page_2(self, client, sample_products):
        """Test pagination - second page"""
        response = client.get("/api/v1/products?page=2&per_page=2")
        assert response.status_code == 200
        result = response.get_json()
        assert len(result["products"]) == 2
        assert result["pagination"]["page"] == 2
        assert result["pagination"]["has_next"] is True
        assert result["pagination"]["has_prev"] is True

    def test_pagination_last_page(self, client, sample_products):
        """Test pagination - last page"""
        response = client.get("/api/v1/products?page=3&per_page=2")
        assert response.status_code == 200
        result = response.get_json()
        assert len(result["products"]) == 1
        assert result["pagination"]["page"] == 3
        assert result["pagination"]["has_next"] is False
        assert result["pagination"]["has_prev"] is True

    def test_combined_filters(self, client, sample_products):
        """Test combining search, filters, and sorting"""
        response = client.get("/api/v1/products?search=gadget&min_price=10&sort_by=price&order=asc")
        assert response.status_code == 200
        result = response.get_json()
        assert len(result["products"]) == 2
        assert all("gadget" in (p["name"].lower() + p["description"].lower()) for p in result["products"])
        prices = [p["price"] for p in result["products"]]
        assert prices == sorted(prices)

    def test_invalid_sort_field(self, client, sample_products):
        """Test error handling for invalid sort field"""
        response = client.get("/api/v1/products?sort_by=invalid_field")
        assert response.status_code == 400
        result = response.get_json()
        assert "error" in result
        assert "Invalid sort_by field" in result["error"]

    def test_invalid_order(self, client, sample_products):
        """Test error handling for invalid order"""
        response = client.get("/api/v1/products?order=invalid")
        assert response.status_code == 400
        result = response.get_json()
        assert "error" in result

    def test_invalid_page(self, client, sample_products):
        """Test error handling for invalid page number"""
        response = client.get("/api/v1/products?page=0")
        assert response.status_code == 400
        result = response.get_json()
        assert "error" in result

    def test_invalid_per_page(self, client, sample_products):
        """Test error handling for invalid per_page value"""
        response = client.get("/api/v1/products?per_page=0")
        assert response.status_code == 400
        result = response.get_json()
        assert "error" in result

    def test_per_page_too_large(self, client, sample_products):
        """Test error handling for per_page exceeding maximum"""
        response = client.get("/api/v1/products?per_page=101")
        assert response.status_code == 400
        result = response.get_json()
        assert "error" in result
