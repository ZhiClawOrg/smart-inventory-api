# Smart Inventory Management API

A lightweight inventory management REST API built with Python Flask.  
This project serves as a demo for **GitHub Copilot Agent HQ** capabilities.

## Features

- Product CRUD operations
- Inventory stock tracking
- Low-stock alerts
- Order management

## Quick Start

```bash
pip install -r requirements.txt
python run.py
```

API runs at `http://localhost:5000`

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/products` | List all products |
| POST | `/api/v1/products` | Create a product |
| GET | `/api/v1/products/<id>` | Get product details |
| PUT | `/api/v1/products/<id>` | Update a product |
| DELETE | `/api/v1/products/<id>` | Delete a product |
| GET | `/api/v1/inventory/low-stock` | Get low-stock alerts |
| POST | `/api/v1/orders` | Place an order |

## Tech Stack

- Python 3.11
- Flask 3.x
- SQLite (development)
- pytest (testing)
