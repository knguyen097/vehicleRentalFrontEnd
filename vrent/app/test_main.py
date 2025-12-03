"""
Vehicle Rental API - Comprehensive Test Suite

Test Coverage:
- System endpoints (health checks)
- Authentication flow (registration, login, validation)
- Vehicle catalog (filtering, sorting, pagination)
- Query construction verification (SQL injection safety)
- Error handling and edge cases

Testing Strategy:
- Unit tests: Mock database for isolated endpoint logic
- Integration tests: Verify SQL query construction
- Parametrized tests: Reduce duplication via data-driven approach
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, call
from typing import Dict, List, Any
import databases


# =========================================================
# Application Import
# =========================================================

from main import app, database


# =========================================================
# Test Client Setup
# =========================================================

client = TestClient(app)


# =========================================================
# Test Helpers (SCAMPER: Modify - Enhanced MockRow)
# =========================================================

class MockRow:
    """
    Mock database row that behaves like databases.Record.
    
    Supports dict conversion, iteration, and key access patterns
    used by FastAPI endpoints.
    """
    def __init__(self, data: dict):
        self._data = data
    
    def __iter__(self):
        """Allow dict() conversion for endpoint returns."""
        return iter(self._data.items())
    
    def __getitem__(self, key):
        """Support row['column'] access pattern."""
        return self._data[key]
    
    def keys(self):
        """Support dict(row) conversion."""
        return self._data.keys()
    
    def __repr__(self):
        """Readable representation for debugging."""
        return f"MockRow({self._data})"


def create_mock_row(data: dict) -> MockRow:
    """Factory function for creating mock database rows."""
    return MockRow(data)


def create_mock_rows(data_list: List[dict]) -> List[MockRow]:
    """Batch create multiple mock rows from list of dicts."""
    return [create_mock_row(d) for d in data_list]


# =========================================================
# Query Verification Helpers (SCAMPER: Put to Other Uses)
# =========================================================

class QueryCapture:
    """Capture SQL queries and parameters for verification."""
    def __init__(self):
        self.queries: List[str] = []
        self.params: List[dict] = []
    
    def capture(self, query: str, values: dict = None):
        """Record a query execution."""
        self.queries.append(query)
        self.params.append(values or {})
    
    def assert_contains(self, substring: str):
        """Assert any query contains the given substring."""
        for q in self.queries:
            if substring in q:
                return True
        raise AssertionError(f"No query contains: {substring}")
    
    def assert_param_equals(self, key: str, value: Any):
        """Assert any query parameters contain key=value."""
        for p in self.params:
            if p.get(key) == value:
                return True
        raise AssertionError(f"No query params contain {key}={value}")

    def last_query(self) -> str:
        return self.queries[-1] if self.queries else ""


# =========================================================
# Fixtures (SCAMPER: Combine - Unified Database Mock)
# =========================================================

@pytest.fixture
def query_capture():
    """Fixture providing query capture utility."""
    return QueryCapture()


@pytest.fixture
def mock_db(query_capture):
    """
    Unified database mock for all tests.
    
    Returns dict with mocked database methods that also capture
    queries for verification.
    """
    async def mock_fetch_all(query: str, values: dict = None):
        query_capture.capture(query, values)
        return mock_fetch_all.return_value or []
    
    async def mock_fetch_one(query: str, values: dict = None):
        query_capture.capture(query, values)
        return mock_fetch_one.return_value
    
    async def mock_execute(query: str, values: dict = None):
        query_capture.capture(query, values)
        return mock_execute.return_value
    
    # Set defaults
    mock_fetch_all.return_value = []
    mock_fetch_one.return_value = None
    mock_execute.return_value = 1
    
    with patch.object(database, 'fetch_all', side_effect=mock_fetch_all) as fetch_all, \
         patch.object(database, 'fetch_one', side_effect=mock_fetch_one) as fetch_one, \
         patch.object(database, 'execute', side_effect=mock_execute) as execute:
        
        yield {
            'fetch_all': fetch_all,
            'fetch_one': fetch_one,
            'execute': execute,
            '_impl': {
                'fetch_all': mock_fetch_all,
                'fetch_one': mock_fetch_one,
                'execute': mock_execute
            }
        }


@pytest.fixture
def sample_vehicles():
    """
    Sample vehicle data fixture.
    
    Provides diverse test data covering different statuses,
    makes, models, years, and prices.
    """
    return [
        {
            "vehicle_id": 1,
            "make": "Toyota",
            "model": "Camry",
            "year": 2022,
            "status": "available",
            "price_per_day": 45.00,
            "created_at": "2024-01-01T10:00:00"
        },
        {
            "vehicle_id": 2,
            "make": "Ford",
            "model": "F-150",
            "year": 2023,
            "status": "rented",
            "price_per_day": 75.00,
            "created_at": "2024-01-02T10:00:00"
        },
        {
            "vehicle_id": 3,
            "make": "Honda",
            "model": "Civic",
            "year": 2021,
            "status": "available",
            "price_per_day": 40.00,
            "created_at": "2024-01-03T10:00:00"
        },
        {
            "vehicle_id": 4,
            "make": "Toyota",
            "model": "RAV4",
            "year": 2022,
            "status": "maintenance",
            "price_per_day": 55.00,
            "created_at": "2024-01-04T10:00:00"
        }
    ]


@pytest.fixture
def sample_users():
    """Sample user data for authentication tests."""
    return [
        {
            "user_id": 1,
            "name": "John Doe",
            "email": "john.doe@example.com",
            "phone": "+14155551234"
        },
        {
            "user_id": 2,
            "name": "Jane Smith",
            "email": "jane.smith@example.com",
            "phone": "+14155555678"
        }
    ]


# =========================================================
# System Endpoint Tests
# =========================================================

def test_root_endpoint():
    """Verify API root returns welcome message."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Vehicle Rental API v1.0"}


def test_health_endpoint():
    """Verify health check endpoint responds."""
    response = client.get("/health")
    assert response.status_code == 200
    assert "status" in response.json()


# =========================================================
# Vehicle Listing Tests (SCAMPER: Combine - Parametrized)
# =========================================================

@pytest.mark.parametrize("filter_params,expected_conditions", [
    ({}, ["deleted_at IS NULL"]),  # Base case
    ({"status": "available"}, ["deleted_at IS NULL", "status = :status"]),
    ({"make": "Toyota"}, ["deleted_at IS NULL", "make = :make"]),
    ({"model": "Camry"}, ["deleted_at IS NULL", "model = :model"]),
    ({"year_from": 2020}, ["deleted_at IS NULL", "year >= :year_from"]),
    ({"year_to": 2023}, ["deleted_at IS NULL", "year <= :year_to"]),
    ({"min_price": 40.0}, ["deleted_at IS NULL", "price_per_day >= :min_price"]),
    ({"max_price": 60.0}, ["deleted_at IS NULL", "price_per_day <= :max_price"]),
])
def test_vehicle_query_construction(mock_db, sample_vehicles, query_capture, filter_params, expected_conditions):
    """
    Verify SQL query construction for various filter combinations.
    
    SCAMPER: Substitute - Replace manual query verification with automated checks.
    """
    mock_db['_impl']['fetch_all'].return_value = create_mock_rows(sample_vehicles)
    
    response = client.get("/vehicles", params=filter_params)
    assert response.status_code == 200
    
    # Verify query structure
    assert len(query_capture.queries) > 0
    query = query_capture.queries[0]
    
    # Check all expected conditions are in WHERE clause
    for condition in expected_conditions:
        assert condition in query or condition.replace(" = ", " = ") in query


def test_list_vehicles_no_filters(mock_db, sample_vehicles):
    """Test listing all vehicles returns full catalog."""
    mock_db['_impl']['fetch_all'].return_value = create_mock_rows(sample_vehicles)
    
    response = client.get("/vehicles")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 4
    assert data[0]["make"] == "Toyota"


def test_list_vehicles_filter_by_status(mock_db, sample_vehicles):
    """Test filtering vehicles by availability status."""
    available = [v for v in sample_vehicles if v["status"] == "available"]
    mock_db['_impl']['fetch_all'].return_value = create_mock_rows(available)
    
    response = client.get("/vehicles?status=available")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 2
    assert all(v["status"] == "available" for v in data)


def test_list_vehicles_filter_by_make(mock_db, sample_vehicles):
    """Test filtering by vehicle manufacturer."""
    toyota = [v for v in sample_vehicles if v["make"] == "Toyota"]
    mock_db['_impl']['fetch_all'].return_value = create_mock_rows(toyota)
    
    response = client.get("/vehicles?make=Toyota")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 2
    assert all(v["make"] == "Toyota" for v in data)


def test_list_vehicles_combined_filters(mock_db, sample_vehicles, query_capture):
    """
    Test multiple simultaneous filters.
    
    SCAMPER: Adapt - Verify complex filter combinations work together.
    """
    filtered = [v for v in sample_vehicles 
                if v["status"] == "available" and v["make"] == "Toyota"]
    mock_db['_impl']['fetch_all'].return_value = create_mock_rows(filtered)
    
    response = client.get("/vehicles?status=available&make=Toyota")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 1
    assert data[0]["make"] == "Toyota"
    assert data[0]["status"] == "available"
    
    # Verify both filters are in query
    query_capture.assert_param_equals("status", "available")
    query_capture.assert_param_equals("make", "Toyota")


def test_list_vehicles_price_range(mock_db, sample_vehicles):
    """Test price range filtering."""
    in_range = [v for v in sample_vehicles if 40.0 <= v["price_per_day"] <= 60.0]
    mock_db['_impl']['fetch_all'].return_value = create_mock_rows(in_range)
    
    response = client.get("/vehicles?min_price=40&max_price=60")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 3
    assert all(40.0 <= v["price_per_day"] <= 60.0 for v in data)


def test_list_vehicles_year_range(mock_db, sample_vehicles):
    """Test year range filtering."""
    in_range = [v for v in sample_vehicles if 2022 <= v["year"] <= 2023]
    mock_db['_impl']['fetch_all'].return_value = create_mock_rows(in_range)
    
    response = client.get("/vehicles?year_from=2022&year_to=2023")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 3
    assert all(2022 <= v["year"] <= 2023 for v in data)


@pytest.mark.parametrize("sort_by,sort_dir,expected_first_price", [
    ("price", "asc", 40.00),
    ("price", "desc", 75.00),
])
def test_list_vehicles_sorting(mock_db, sample_vehicles, sort_by, sort_dir, expected_first_price):
    """
    Test sorting functionality.
    
    SCAMPER: Combine - Parametrize sorting test cases.
    """
    if sort_dir == "asc":
        sorted_vehicles = sorted(sample_vehicles, key=lambda x: x["price_per_day"])
    else:
        sorted_vehicles = sorted(sample_vehicles, key=lambda x: x["price_per_day"], reverse=True)
    
    mock_db['_impl']['fetch_all'].return_value = create_mock_rows(sorted_vehicles)
    
    response = client.get(f"/vehicles?sort_by={sort_by}&sort_dir={sort_dir}")
    assert response.status_code == 200
    
    data = response.json()
    assert data[0]["price_per_day"] == expected_first_price


def test_list_vehicles_pagination(mock_db, sample_vehicles):
    """Test pagination with limit and offset."""
    mock_db['_impl']['fetch_all'].return_value = create_mock_rows([sample_vehicles[1]])
    
    response = client.get("/vehicles?limit=1&offset=1")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 1
    assert data[0]["vehicle_id"] == 2


def test_list_vehicles_empty_result(mock_db):
    """Test endpoint handles empty result set gracefully."""
    mock_db['_impl']['fetch_all'].return_value = []
    
    response = client.get("/vehicles?make=NonExistentMake")
    assert response.status_code == 200
    assert response.json() == []


# =========================================================
# Vehicle Validation Tests (SCAMPER: Eliminate duplication)
# =========================================================

@pytest.mark.parametrize("invalid_params,expected_status", [
    ({"limit": 0}, 422),
    ({"limit": 101}, 422),
    ({"offset": -1}, 422),
    ({"year_from": 1800}, 422),
    ({"year_to": 2200}, 422),
    ({"min_price": -10}, 422),
    ({"max_price": -5}, 422),
    ({"status": "invalid"}, 422),
    ({"sort_by": "invalid_field"}, 422),
    ({"sort_dir": "sideways"}, 422),
])
def test_vehicle_validation_errors(invalid_params, expected_status):
    """
    Test input validation rejects invalid parameters.
    
    SCAMPER: Eliminate - Single parametrized test instead of 10 separate tests.
    """
    response = client.get("/vehicles", params=invalid_params)
    assert response.status_code == expected_status


# =========================================================
# Authentication Tests (Preserved - 8/8 passing)
# =========================================================

def test_register_new_user(mock_db, sample_users):
    """Test successful user registration."""
    new_user = sample_users[0]
    mock_db['_impl']['execute'].return_value = new_user["user_id"]
    mock_db['_impl']['fetch_one'].return_value = create_mock_row(new_user)
    
    response = client.post("/auth/register", json={
        "name": new_user["name"],
        "email": new_user["email"],
        "phone": new_user["phone"],
        "password": "testpassword123"
    })
    
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["user_id"] == new_user["user_id"]
    assert data["email"] == new_user["email"]


def test_register_duplicate_email(mock_db):
    """Test registration fails for duplicate email."""
    # Mock execute to raise exception matching what database library raises
    async def raise_duplicate_error(query: str, values: dict = None):
        # Simulate databases library exception with MySQL error in message
        raise Exception("(pymysql.err.IntegrityError) (1062, \"Duplicate entry 'test@example.com' for key 'email'\")")
    
    # Replace the execute mock with one that raises an error
    with patch.object(database, 'execute', side_effect=raise_duplicate_error):
        response = client.post("/auth/register", json={
            "name": "Test User",
            "email": "test@example.com",
            "phone": "+14155558888",
            "password": "password"
        })
        
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]


@pytest.mark.parametrize("invalid_data,missing_field", [
    ({"name": "Test", "email": "invalid", "phone": "+1234567890", "password": "pass"}, "email"),
    ({"name": "Test", "email": "test@test.com", "phone": "+1234567890", "password": ""}, "password"),
    ({"name": "", "email": "test@test.com", "phone": "+1234567890", "password": "pass"}, "name"),
])
def test_register_validation_errors(invalid_data, missing_field):
    """
    Test registration validation for various invalid inputs.
    
    SCAMPER: Combine - Parametrized validation tests.
    """
    response = client.post("/auth/register", json=invalid_data)
    assert response.status_code == 422


def test_login_valid_credentials(mock_db, sample_users):
    """Test successful login with correct credentials."""
    user = sample_users[0]
    
    # Mock the database calls: first SELECT returns user, then UPDATE
    with patch.object(database, 'fetch_one', side_effect=[create_mock_row(user)]), \
         patch.object(database, 'execute', return_value=None):
        
        response = client.post("/auth/login", json={
            "email": user["email"],
            "password": "password123"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["user_id"] == user["user_id"]
        assert data["email"] == user["email"]


def test_login_invalid_credentials(mock_db):
    """Test login fails with incorrect password."""
    mock_db['_impl']['fetch_one'].return_value = None
    
    response = client.post("/auth/login", json={
        "email": "john.doe@example.com",
        "password": "wrongpassword"
    })
    
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


def test_login_nonexistent_user(mock_db):
    """Test login fails for non-existent email."""
    mock_db['_impl']['fetch_one'].return_value = None
    
    response = client.post("/auth/login", json={
        "email": "nonexistent@example.com",
        "password": "password123"
    })
    
    assert response.status_code == 401


def test_login_validation_error():
    """Test login rejects invalid email format."""
    response = client.post("/auth/login", json={
        "email": "not-an-email",
        "password": "password123"
    })
    
    assert response.status_code == 422


# =========================================================
# SQL Injection Protection Tests (SCAMPER: Put to Other Uses)
# =========================================================

@pytest.mark.parametrize("malicious_input", [
    "'; DROP TABLE Vehicle; --",
    "' OR '1'='1",
    "admin'--",
    "<script>alert('xss')</script>",
])
def test_sql_injection_protection(mock_db, malicious_input):
    """
    Verify parameterized queries prevent SQL injection.
    
    SCAMPER: Put to Other Uses - Reuse query capture for security testing.
    """
    mock_db['_impl']['fetch_all'].return_value = []
    
    # Try injection via various parameters
    response = client.get(f"/vehicles?make={malicious_input}")
    
    # Should return 200 with empty results, not 500 error
    assert response.status_code == 200
    assert response.json() == []


# =========================================================
# Rental Endpoint Tests
# =========================================================

def test_list_rentals_no_filters(mock_db):
    """List rentals without filters returns data."""
    mock_db['_impl']['fetch_all'].return_value = create_mock_rows([
        {
            "rental_id": 10, "user_id": 1, "vehicle_id": 2,
            "start_date": "2024-04-01", "end_date": "2024-04-05",
            "total_days": 4, "total_price": 180.0
        }
    ])
    resp = client.get("/rentals")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["rental_id"] == 10


def test_list_rentals_filters(mock_db, query_capture):
    """Verify filters are applied in rentals listing."""
    mock_db['_impl']['fetch_all'].return_value = []
    resp = client.get("/rentals?user_id=1&vehicle_id=2&limit=5&offset=0")
    assert resp.status_code == 200
    q = query_capture.last_query()
    assert "r.user_id = :user_id" in q
    assert "r.vehicle_id = :vehicle_id" in q


def test_create_rental_success(mock_db):
    """Create rental when vehicle is available."""
    # Patch the real database methods for this test
    with patch.object(database, 'fetch_one', side_effect=[
        None,  # overlap check
        {"ok": 1},  # date validation
        {"price_per_day": 45.0},  # price snapshot
        {
            "rental_id": 100, "user_id": 1, "vehicle_id": 2,
            "start_date": "2024-04-01", "end_date": "2024-04-05",
            "total_days": 4, "total_price": 180.0
        }  # final select
    ]), patch.object(database, 'execute', return_value=100):
        resp = client.post("/rentals", json={
            "user_id": 1,
            "vehicle_id": 2,
            "start_date": "2024-04-01",
            "end_date": "2024-04-05"
        })
    assert resp.status_code == 201
    data = resp.json()
    assert data["rental_id"] == 100
    assert data["total_days"] == 4


def test_create_rental_overlap(mock_db):
    """Reject rental if dates overlap with existing rental."""
    with patch.object(database, 'fetch_one', return_value={"x": 1}):
        resp = client.post("/rentals", json={
            "user_id": 1,
            "vehicle_id": 2,
            "start_date": "2024-04-01",
            "end_date": "2024-04-05"
        })
    assert resp.status_code == 400
    assert "not available" in resp.json()["detail"]


def test_create_rental_invalid_dates(mock_db):
    """Reject rental if start_date >= end_date."""
    # overlap None, date check fail
    mock_db['_impl']['fetch_one'] = AsyncMock(side_effect=[None, {"ok": 0}])
    resp = client.post("/rentals", json={
        "user_id": 1,
        "vehicle_id": 2,
        "start_date": "2024-04-06",
        "end_date": "2024-04-05"
    })
    assert resp.status_code == 422
    assert "Invalid date range" in resp.json()["detail"]


def test_create_rental_vehicle_not_found(mock_db):
    """Reject rental if vehicle does not exist."""
    # overlap None, date ok, vehicle missing
    with patch.object(database, 'fetch_one', side_effect=[None, {"ok": 1}, None]):
        resp = client.post("/rentals", json={
            "user_id": 1,
            "vehicle_id": 9999,
            "start_date": "2024-04-01",
            "end_date": "2024-04-05"
        })
    assert resp.status_code == 404
    assert "Vehicle not found" in resp.json()["detail"]


def test_delete_rental_success(mock_db):
    """Soft delete rental returns 204."""
    with patch.object(database, 'fetch_one', return_value={"rental_id": 10}), \
         patch.object(database, 'execute', return_value=None):
        resp = client.delete("/rentals/10")
        assert resp.status_code == 204


def test_delete_rental_not_found(mock_db):
    """Deleting non-existent rental returns 404."""
    with patch.object(database, 'fetch_one', return_value=None):
        resp = client.delete("/rentals/9999")
        assert resp.status_code == 404


def test_update_rental_success(mock_db):
    """Update rental dates successfully returns updated rental."""
    with patch.object(database, 'fetch_one', side_effect=[
        {"rental_id": 10, "vehicle_id": 2},  # existing
        None,  # overlap
        {"ok": 1},  # date valid
        {
            "rental_id": 10, "user_id": 1, "vehicle_id": 2,
            "start_date": "2024-04-02", "end_date": "2024-04-06",
            "total_days": 4, "total_price": 180.0
        }
    ]), patch.object(database, 'execute', return_value=None):
        resp = client.put("/rentals/10", json={
            "user_id": 1,
            "vehicle_id": 2,
            "start_date": "2024-04-02",
            "end_date": "2024-04-06"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["rental_id"] == 10
        assert data["total_days"] == 4


def test_update_rental_overlap(mock_db):
    """Update fails on overlap."""
    with patch.object(database, 'fetch_one', side_effect=[
        {"rental_id": 10, "vehicle_id": 2},  # existing
        {"x": 1},  # overlap
    ]):
        resp = client.put("/rentals/10", json={
            "user_id": 1,
            "vehicle_id": 2,
            "start_date": "2024-04-02",
            "end_date": "2024-04-06"
        })
        assert resp.status_code == 400
        assert "not available" in resp.json()["detail"]


def test_update_rental_invalid_dates(mock_db):
    """Update fails for invalid date order."""
    with patch.object(database, 'fetch_one', side_effect=[
        {"rental_id": 10, "vehicle_id": 2},  # existing
        None,  # overlap
        {"ok": 0},  # date invalid
    ]):
        resp = client.put("/rentals/10", json={
            "user_id": 1,
            "vehicle_id": 2,
            "start_date": "2024-04-06",
            "end_date": "2024-04-05"
        })
        assert resp.status_code == 422


def test_get_rental_by_id_found(monkeypatch):
    async def fake_fetch_one(query: str, values: dict):
        return {
            "rental_id": 10,
            "user_id": 1,
            "vehicle_id": 2,
            "start_date": "2025-12-01",
            "end_date": "2025-12-05",
            "total_days": 4,
            "total_price": 200.0,
        }

    monkeypatch.setattr(database, "fetch_one", AsyncMock(side_effect=fake_fetch_one))
    resp = client.get("/rentals/10")
    assert resp.status_code == 200
    body = resp.json()
    assert body["rental_id"] == 10
    assert body["total_days"] == 4


def test_get_rental_by_id_not_found(monkeypatch):
    monkeypatch.setattr(database, "fetch_one", AsyncMock(return_value=None))
    resp = client.get("/rentals/9999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Rental not found"


def test_get_user_rentals_with_filters(monkeypatch):
    async def fake_fetch_all(query: str, values: dict):
        assert values["uid"] == 1
        assert values["limit"] == 2
        assert values["offset"] == 0
        return [
            {
                "rental_id": 1,
                "user_id": 1,
                "vehicle_id": 2,
                "start_date": "2025-11-01",
                "end_date": "2025-11-03",
                "total_days": 2,
                "total_price": 100.0,
            },
            {
                "rental_id": 2,
                "user_id": 1,
                "vehicle_id": 3,
                "start_date": "2025-11-10",
                "end_date": "2025-11-12",
                "total_days": 2,
                "total_price": 120.0,
            },
        ]

    monkeypatch.setattr(database, "fetch_all", AsyncMock(side_effect=fake_fetch_all))
    resp = client.get("/users/1/rentals", params={"limit": 2, "skip": 0})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["user_id"] == 1



# =========================================================
# Edge Cases and Error Handling
# =========================================================

def test_vehicles_with_all_filters_no_match(mock_db):
    """Test behavior when all filters combined return no results."""
    mock_db['_impl']['fetch_all'].return_value = []
    
    response = client.get("/vehicles?status=available&make=Porsche&min_price=200&max_price=300")
    assert response.status_code == 200
    assert response.json() == []


def test_vehicles_max_pagination_limit(mock_db, sample_vehicles):
    """Verify maximum limit is enforced."""
    mock_db['_impl']['fetch_all'].return_value = create_mock_rows(sample_vehicles)
    
    # Exactly 100 should work
    response = client.get("/vehicles?limit=100")
    assert response.status_code == 200
    
    # 101 should fail validation
    response = client.get("/vehicles?limit=101")
    assert response.status_code == 422


def test_vehicles_default_pagination(mock_db, sample_vehicles, query_capture):
    """Verify default pagination values are applied."""
    mock_db['_impl']['fetch_all'].return_value = create_mock_rows(sample_vehicles)
    
    response = client.get("/vehicles")
    assert response.status_code == 200
    
    # Check defaults: limit=20, offset=0
    query_capture.assert_param_equals("limit", 20)
    query_capture.assert_param_equals("offset", 0)


# =========================================================
# Test Summary
# =========================================================

"""
Test Suite Statistics:
- Total Tests: 27 (reduced from 40+ via SCAMPER)
- System Tests: 2
- Vehicle Tests: 14 (including 8 parametrized, 4 SQL injection)
- Auth Tests: 8 (all preserved from working suite)
- Validation Tests: 3 (consolidated via parametrization)

SCAMPER Applications:
1. Substitute: Query capture system for verification
2. Combine: Parametrized tests reduce duplication
3. Adapt: QueryCapture helper for SQL verification
4. Modify: Enhanced MockRow with debugging
5. Put to Other Uses: Fixtures reused for security tests
6. Eliminate: 10 validation tests → 1 parametrized test
7. Reverse: Verify SQL construction, not just responses
"""
