"""
Vehicle Rental API - FastAPI Backend

A RESTful API for managing vehicle rentals with user authentication.
Provides endpoints for vehicle listing, filtering, user registration, and login.

Features:
- Vehicle catalog with advanced filtering and sorting
- User authentication with SHA2-256 password hashing
- MariaDB database integration
- CORS-enabled for frontend integration

Author: Vehicle Rental System Team
License: MIT
"""

from fastapi import FastAPI, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Optional, Literal, List
from pydantic import BaseModel, EmailStr, Field
from datetime import date
import os
import databases


# =========================================================
# Configuration
# =========================================================

DATABASE_URL = os.getenv("DATABASE_URL")
database = databases.Database(DATABASE_URL)


# =========================================================
# FastAPI Application Setup
# =========================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await database.connect()
    try:
        yield
    finally:
        # Shutdown
        await database.disconnect()


app = FastAPI(
    title="Vehicle Rental API",
    description="Backend API for vehicle rental management system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Enable CORS for frontend integration (dev mode - all origins allowed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# Pydantic Models - Request/Response Schemas
# =========================================================

class AuthLoginRequest(BaseModel):
    """Login request payload."""
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., min_length=1, description="User's password")
    
    model_config = {
        "json_schema_extra": {
            "examples": [{
                "email": "john.doe@example.com",
                "password": "password123"
            }]
        }
    }


class AuthRegisterRequest(BaseModel):
    """User registration request payload."""
    name: str = Field(..., min_length=1, max_length=100, description="Full name")
    email: EmailStr = Field(..., description="Unique email address")
    phone: str = Field(..., min_length=7, max_length=20, description="Phone number (international format)")
    password: str = Field(..., min_length=1, description="Password (min 1 char for demo)")
    
    model_config = {
        "json_schema_extra": {
            "examples": [{
                "name": "John Doe",
                "email": "john.doe@example.com",
                "phone": "+14155551234",
                "password": "securepassword123"
            }]
        }
    }


class AuthResponse(BaseModel):
    """Authentication response with user details."""
    success: bool = Field(..., description="Whether the operation succeeded")
    message: str = Field(..., description="Human-readable message")
    user_id: Optional[int] = Field(None, description="User ID (if successful)")
    name: Optional[str] = Field(None, description="User's full name (if successful)")
    email: Optional[str] = Field(None, description="User's email (if successful)")
    
    model_config = {
        "json_schema_extra": {
            "examples": [{
                "success": True,
                "message": "Login successful",
                "user_id": 1,
                "name": "John Doe",
                "email": "john.doe@example.com"
            }]
        }
    }


class RentalCreateRequest(BaseModel):
    """Create rental request payload."""
    user_id: int = Field(..., gt=0, description="User ID")
    vehicle_id: int = Field(..., gt=0, description="Vehicle ID")
    start_date: date = Field(..., description="Rental start date (YYYY-MM-DD)")
    end_date: date = Field(..., description="Rental end date (YYYY-MM-DD)")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "user_id": 1,
                "vehicle_id": 2,
                "start_date": "2024-04-01",
                "end_date": "2024-04-05"
            }]
        }
    }


class RentalResponse(BaseModel):
    """Rental response object."""
    rental_id: int
    user_id: int
    vehicle_id: int
    make: Optional[str] = None
    model: Optional[str] = None
    start_date: date
    end_date: date
    total_days: int
    total_price: float
    
class RentalCreate(BaseModel):
    user_id: int
    vehicle_id: int
    start_date: date
    end_date: date

# =========================================================
# Lifespan handled via async context manager above
# =========================================================


# =========================================================
# Core Endpoints
# =========================================================

@app.get("/", tags=["System"])
async def root():
    """Root endpoint - API welcome message."""
    return {"message": "Vehicle Rental API v1.0"}


@app.get("/health", tags=["System"])
async def health():
    """
    Health check endpoint for monitoring and load balancers.
    
    Returns:
        dict: Status object with API and database connection state
    """
    db_state = "connected" if getattr(database, "is_connected", False) else "disconnected"
    return {"status": "ok", "db": db_state}


# =========================================================
# Vehicle Endpoints
# =========================================================

@app.get("/vehicles", tags=["Vehicles"])
async def list_vehicles(
    status: Optional[Literal["available", "rented", "maintenance"]] = Query(
        None, 
        description="Filter by vehicle availability status",
        examples=["available"]
    ),
    make: Optional[str] = Query(None, description="Filter by manufacturer", examples=["Toyota"]),
    model: Optional[str] = Query(None, description="Filter by model name", examples=["Camry"]),
    year_from: Optional[int] = Query(None, ge=1900, le=2100, description="Minimum manufacturing year (inclusive)", examples=[2020]),
    year_to: Optional[int] = Query(None, ge=1900, le=2100, description="Maximum manufacturing year (inclusive)", examples=[2024]),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum daily rental price in USD", examples=[25.00]),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum daily rental price in USD", examples=[100.00]),
    sort_by: Optional[Literal["price", "year", "created_at"]] = Query(
        "created_at",
        description="Sort field (price=price_per_day, year=manufacturing year, created_at=date added to catalog)",
        examples=["price"]
    ),
    sort_dir: Optional[Literal["asc", "desc"]] = Query("asc", description="Sort direction (asc=ascending, desc=descending)", examples=["asc"]),
    limit: int = Query(20, ge=1, le=100, description="Maximum results per page (1-100)", examples=[20]),
    offset: int = Query(0, ge=0, description="Results to skip for pagination (0-based)", examples=[0]),
):
    """
    List and filter vehicles from the rental catalog.
    
    Supports advanced filtering, sorting, and pagination. All filters are optional and combine with AND logic.
    Only returns non-deleted vehicles (deleted_at IS NULL).
    
    **Example queries:**
    - Available Toyotas: `?status=available&make=Toyota`
    - Affordable recent cars: `?year_from=2020&max_price=60&sort_by=price&sort_dir=asc`
    - Paginated results: `?limit=10&offset=20` (page 3)
    
    **Returns:** Array of vehicle objects (empty array if no matches)
    """
    # Build WHERE clause dynamically
    where = ["deleted_at IS NULL"]  # Exclude soft-deleted vehicles
    values = {}
    
    # Simple equality filters
    for param, column in [("status", "status"), ("make", "make"), ("model", "model")]:
        if locals()[param]:
            where.append(f"{column} = :{param}")
            values[param] = locals()[param]
    
    # Range filters
    if year_from is not None:
        where.append("year >= :year_from")
        values["year_from"] = year_from
    if year_to is not None:
        where.append("year <= :year_to")
        values["year_to"] = year_to
    if min_price is not None:
        where.append("price_per_day >= :min_price")
        values["min_price"] = min_price
    if max_price is not None:
        where.append("price_per_day <= :max_price")
        values["max_price"] = max_price
    
    # Map sort_by parameter to actual column name
    sort_column_map = {
        "price": "price_per_day",
        "year": "year",
        "created_at": "created_at"
    }
    sort_column = sort_column_map.get(sort_by, "created_at")
    
    # Build complete SQL query
    where_clause = " AND ".join(where)
    query = f"""
        SELECT vehicle_id, make, model, year, status, price_per_day, created_at
        FROM Vehicle
        WHERE {where_clause}
        ORDER BY {sort_column} {sort_dir.upper()}
        LIMIT :limit OFFSET :offset
    """
    
    # Add pagination parameters
    values["limit"] = limit
    values["offset"] = offset
    
    # Execute query and return results
    rows = await database.fetch_all(query, values)
    return [dict(row) for row in rows]


# =========================================================
# Authentication Endpoints
# =========================================================

@app.post("/auth/register", response_model=AuthResponse, status_code=201, tags=["Authentication"])
async def register(payload: AuthRegisterRequest):
    """
    Register a new user account.
    
    Creates a new user with hashed password stored in the database.
    Password hashing uses MariaDB's SHA2-256 built-in function.
    
    **Security Note:** SHA2-256 is used for educational/demo purposes.
    Production systems should use bcrypt or Argon2 with proper salting.
    
    Args:
        payload: Registration data (name, email, phone, password)
        
    Returns:
        AuthResponse: Success status with new user details
        
    Raises:
        HTTPException 400: Email or phone already registered
        HTTPException 422: Invalid input format (Pydantic validation)
        HTTPException 500: Database or server error
    """
    try:
        # Insert new user with SHA2-hashed password
        query = """
            INSERT INTO User (name, email, phone, password_hash)
            VALUES (:name, :email, :phone, SHA2(:password, 256))
        """
        result = await database.execute(
            query,
            {
                "name": payload.name,
                "email": payload.email,
                "phone": payload.phone,
                "password": payload.password,
            },
        )
        
        # Fetch the newly created user
        user = await database.fetch_one(
            "SELECT user_id, name, email FROM User WHERE user_id = :uid",
            {"uid": result},
        )
        
        return AuthResponse(
            success=True,
            message="Registration successful",
            user_id=user["user_id"],
            name=user["name"],
            email=user["email"],
        )
    
    except Exception as e:
        # Handle duplicate email or phone (MySQL/MariaDB error code 1062)
        error_msg = str(e).lower()
        if "duplicate" in error_msg or "1062" in error_msg:
            if "email" in error_msg:
                raise HTTPException(status_code=400, detail="Email already registered")
            elif "phone" in error_msg:
                raise HTTPException(status_code=400, detail="Phone number already registered")
            else:
                raise HTTPException(status_code=400, detail="Registration failed: duplicate entry")
        raise HTTPException(status_code=500, detail="Registration failed")


@app.post("/auth/login", response_model=AuthResponse, tags=["Authentication"])
async def login(payload: AuthLoginRequest):
    """
    Authenticate user and initiate session.
    
    Verifies user credentials by comparing the provided password against
    the stored SHA2-256 hash in the database. Updates last login timestamp
    on successful authentication.
    
    **Security Note:** Password verification happens in the database using
    SHA2-256 for demo purposes. Production systems should use bcrypt/Argon2
    with application-level verification.
    
    Args:
        payload: Login credentials (email and password)
        
    Returns:
        AuthResponse: Success status with user details
        
    Raises:
        HTTPException 401: Invalid credentials or user not found
        HTTPException 422: Invalid input format (Pydantic validation)
    """
    # Query user with matching email and password hash
    # Note: Password verification happens in SQL via SHA2 comparison
    user = await database.fetch_one(
        """
        SELECT user_id, name, email
        FROM User
        WHERE email = :email 
          AND password_hash = SHA2(:password, 256)
          AND deleted_at IS NULL
        """,
        {"email": payload.email, "password": payload.password},
    )
    
    if not user:
        # Return generic error to prevent user enumeration
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )
    
    # Update last login timestamp for activity tracking
    await database.execute(
        "UPDATE User SET last_login_at = CURRENT_TIMESTAMP WHERE user_id = :uid",
        {"uid": user["user_id"]},
    )
    
    return AuthResponse(
        success=True,
        message="Login successful",
        user_id=user["user_id"],
        name=user["name"],
        email=user["email"],
    )


# =========================================================
# Rental Endpoints
# =========================================================

@app.get("/rentals", response_model=List[RentalResponse], tags=["Rentals"])
async def list_rentals(
    user_id: Optional[int] = Query(None, gt=0, description="Filter by user ID", examples=[1]),
    vehicle_id: Optional[int] = Query(None, gt=0, description="Filter by vehicle ID", examples=[5]),
    limit: int = Query(20, ge=1, le=100, description="Max results per page (1-100)", examples=[20]),
    offset: int = Query(0, ge=0, description="Pagination offset (0-based)", examples=[0]),
):
    """
    List all rentals with optional filtering and pagination.
    
    Automatically calculates `total_days` using DATEDIFF and `total_price` as days × daily_rate.
    Results ordered by start_date (most recent first).
    
    **Example queries:**
    - User's rentals: `?user_id=1`
    - Vehicle history: `?vehicle_id=5`
    - Combined filter: `?user_id=1&vehicle_id=5`
    """
    where = ["r.deleted_at IS NULL"]
    values = {"limit": limit, "offset": offset}
    if user_id:
        where.append("r.user_id = :user_id")
        values["user_id"] = user_id
    if vehicle_id:
        where.append("r.vehicle_id = :vehicle_id")
        values["vehicle_id"] = vehicle_id

    query = f"""
        SELECT r.rental_id, r.user_id, r.vehicle_id, r.start_date, r.end_date,
               DATEDIFF(r.end_date, r.start_date) AS total_days,
               (DATEDIFF(r.end_date, r.start_date) * v.price_per_day) AS total_price
        FROM Rental r
        JOIN Vehicle v ON v.vehicle_id = r.vehicle_id
        WHERE {' AND '.join(where)}
        ORDER BY r.start_date DESC
        LIMIT :limit OFFSET :offset
    """

    rows = await database.fetch_all(query, values)
    return [dict(row) for row in rows]

@app.get(
    "/rentals/{rental_id}",
    response_model=RentalResponse,
    tags=["Rentals"],
    responses={
        404: {"description": "Rental not found or deleted"},
    },
)
async def get_rental_by_id(rental_id: int):
    """Retrieve a single rental by ID with calculated totals."""
    query = (
        "SELECT r.id AS rental_id, r.user_id, r.vehicle_id, r.start_date, r.end_date, "
        "DATEDIFF(r.end_date, r.start_date) AS total_days, "
        "DATEDIFF(r.end_date, r.start_date) * v.daily_rate AS total_price "
        "FROM rentals r JOIN vehicles v ON v.id = r.vehicle_id "
        "WHERE r.deleted_at IS NULL AND r.id = :rid"
    )
    row = await database.fetch_one(query=query, values={"rid": rental_id})
    if not row:
        raise HTTPException(status_code=404, detail="Rental not found")
    return dict(row)

@app.get(
    "/users/{user_id}/rentals",
    response_model=List[RentalResponse],
    tags=["Rentals"],
)
async def get_user_rentals(
    user_id: int,
    vehicle_id: int | None = Query(default=None, ge=1, description="Optional: filter by vehicle ID", examples=[5]),
    skip: int = Query(default=0, ge=0, description="Pagination offset", examples=[0]),
    limit: int = Query(default=50, ge=1, le=200, description="Max results (1-200)", examples=[50]),
):
    """
    Get all rentals for a specific user.

    Optionally filter by vehicle_id to see user's history with a specific vehicle.
    Results ordered by start_date (most recent first).
    """
    where = ["r.deleted_at IS NULL", "r.user_id = :uid"]
    values: dict[str, object] = {"uid": user_id}

    if vehicle_id is not None:
        where.append("r.vehicle_id = :vid")
        values["vid"] = vehicle_id

    query = f"""
        SELECT
            r.rental_id,
            r.user_id,
            r.vehicle_id,
            v.make,
            v.model,
            r.start_date,
            r.end_date,
            DATEDIFF(r.end_date, r.start_date) AS total_days,
            r.total_cost AS total_price
        FROM Rental r
        JOIN Vehicle v ON v.vehicle_id = r.vehicle_id
        WHERE {' AND '.join(where)}
        ORDER BY r.start_date DESC
        LIMIT :limit OFFSET :offset
    """

    values.update({"limit": limit, "offset": skip})
    rows = await database.fetch_all(query=query, values=values)
    return [dict(r) for r in rows]



@app.post(
    "/rentals",
    response_model=RentalResponse,
    status_code=201,
    tags=["Rentals"],
    responses={
        400: {
            "description": "Vehicle not available (date overlap with existing rental)",
            "content": {"application/json": {"example": {"detail": "Vehicle not available in the selected dates"}}},
        },
        404: {
            "description": "Vehicle not found or deleted",
            "content": {"application/json": {"example": {"detail": "Vehicle not found"}}},
        },
        422: {
            "description": "Invalid date range (start_date >= end_date) or validation error",
            "content": {"application/json": {"example": {"detail": "Invalid date range: start_date must be before end_date"}}},
        },
    },
)
async def create_rental(payload: RentalCreateRequest):
    """
    Create a new rental for a vehicle, with overlap checks and
    a graceful fallback for the uq_vehicle_date_overlap constraint.
    """

    user_id = payload.user_id
    vehicle_id = payload.vehicle_id
    start_date = payload.start_date
    end_date = payload.end_date

    # 1) Validate date range
    if end_date < start_date:
        raise HTTPException(
            status_code=422,
            detail="Invalid date range: start_date must be before end_date",
        )

    # 2) Check for ANY overlapping rental for the same vehicle
    #    NOTE: we do NOT filter by deleted_at here, because the DB UNIQUE constraint
    #    does not, and would still block a reinsert with the same dates.
    overlap = await database.fetch_one(
        """
        SELECT 1
        FROM Rental
        WHERE vehicle_id = :vehicle_id
          AND NOT (:end_date < start_date OR :start_date > end_date)
        LIMIT 1
        """,
        {
            "vehicle_id": vehicle_id,
            "start_date": start_date,
            "end_date": end_date,
        },
    )

    if overlap:
        raise HTTPException(
            status_code=400,
            detail="Vehicle not available in the selected dates",
        )

    # 3) Get vehicle pricing
    vehicle = await database.fetch_one(
        """
        SELECT price_per_day
        FROM Vehicle
        WHERE vehicle_id = :vehicle_id
          AND deleted_at IS NULL
        """,
        {"vehicle_id": vehicle_id},
    )

    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    price_per_day = float(vehicle["price_per_day"])

    # 4) Compute total days and cost (inclusive of both start and end dates)
    total_days = (end_date - start_date).days + 1
    total_cost = round(price_per_day * total_days, 2)

    # 5) Insert rental, catching any remaining 1062 errors
    try:
        rental_id = await database.execute(
            """
            INSERT INTO Rental (
                user_id,
                vehicle_id,
                start_date,
                end_date,
                price_at_rental,
                total_cost
            ) VALUES (
                :user_id,
                :vehicle_id,
                :start_date,
                :end_date,
                :price_at_rental,
                :total_cost
            )
            """,
            {
                "user_id": user_id,
                "vehicle_id": vehicle_id,
                "start_date": start_date,
                "end_date": end_date,
                "price_at_rental": price_per_day,
                "total_cost": total_cost,
            },
        )
    except Exception as e:
        msg = str(e)
        # Safety net in case the UNIQUE constraint still triggers
        if "1062" in msg and "uq_vehicle_date_overlap" in msg:
            raise HTTPException(
                status_code=400,
                detail="Vehicle not available in the selected dates",
            )
        # Anything else is a genuine server error
        raise HTTPException(status_code=500, detail="Failed to create rental")

    # 6) Respond with the new rental; My Rentals will later load make/model via the history endpoint
    return RentalResponse(
        rental_id=rental_id,
        user_id=user_id,
        vehicle_id=vehicle_id,
        make=None,
        model=None,
        start_date=start_date,
        end_date=end_date,
        total_days=total_days,
        total_price=total_cost,
    )


@app.delete(
    "/rentals/{rental_id}",
    status_code=204,
    tags=["Rentals"],
    responses={
        404: {
            "description": "Rental not found or already deleted",
            "content": {"application/json": {"example": {"detail": "Rental not found"}}},
        },
    },
)
async def delete_rental(rental_id: int):
    """
    Cancel/delete a rental (soft delete).
    
    Sets `deleted_at` timestamp without removing from database.
    Deleted rentals are excluded from all GET queries.
    Operation is idempotent (returns 404 if already deleted).
    """
    # Verify rental exists and not already deleted
    existing = await database.fetch_one(
        "SELECT rental_id FROM Rental WHERE rental_id = :rid AND deleted_at IS NULL",
        {"rid": rental_id},
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Rental not found")

    await database.execute(
        "UPDATE Rental SET deleted_at = CURRENT_TIMESTAMP WHERE rental_id = :rid",
        {"rid": rental_id},
    )
    return None


@app.put(
    "/rentals/{rental_id}",
    response_model=RentalResponse,
    tags=["Rentals"],
    responses={
        400: {
            "description": "Vehicle not available (date overlap with other rentals)",
            "content": {"application/json": {"example": {"detail": "Vehicle not available in the selected dates"}}},
        },
        404: {
            "description": "Rental not found or deleted",
            "content": {"application/json": {"example": {"detail": "Rental not found"}}},
        },
        422: {
            "description": "Invalid date range (start_date >= end_date)",
            "content": {"application/json": {"example": {"detail": "Invalid date range: start_date must be before end_date"}}},
        },
    },
)
async def update_rental(rental_id: int, payload: RentalCreateRequest):
    """
    Update rental dates with availability re-validation.
    
    **Validations:**
    1. Rental exists and is not deleted
    2. No overlapping rentals for the same vehicle (excludes current rental from check)
    3. start_date < end_date
    
    Updates `updated_at` timestamp and recalculates totals based on current vehicle pricing.
    Note: vehicle_id cannot be changed; uses existing vehicle from database.
    """
    # Ensure rental exists
    existing = await database.fetch_one(
        "SELECT rental_id, vehicle_id FROM Rental WHERE rental_id = :rid AND deleted_at IS NULL",
        {"rid": rental_id},
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Rental not found")

    vehicle_id = existing["vehicle_id"]

    # Overlap check excluding current rental
    overlap = await database.fetch_one(
        """
        SELECT 1 FROM Rental
        WHERE vehicle_id = :vehicle_id
          AND rental_id <> :rid
          AND deleted_at IS NULL
          AND NOT (:end_date <= start_date OR :start_date >= end_date)
        LIMIT 1
        """,
        {
            "vehicle_id": vehicle_id,
            "rid": rental_id,
            "start_date": str(payload.start_date),
            "end_date": str(payload.end_date),
        },
    )
    if overlap:
        raise HTTPException(status_code=400, detail="Vehicle not available in the selected dates")

    # Date order validation
    valid = await database.fetch_one(
        "SELECT CASE WHEN :start_date < :end_date THEN 1 ELSE 0 END AS ok",
        {"start_date": str(payload.start_date), "end_date": str(payload.end_date)},
    )
    if not valid or valid["ok"] != 1:
        raise HTTPException(status_code=422, detail="Invalid date range: start_date must be before end_date")

    await database.execute(
        """
        UPDATE Rental
        SET start_date = :start_date, end_date = :end_date, updated_at = CURRENT_TIMESTAMP
        WHERE rental_id = :rid
        """,
        {
            "start_date": str(payload.start_date),
            "end_date": str(payload.end_date),
            "rid": rental_id,
        },
    )

    # Return updated view
    row = await database.fetch_one(
        """
        SELECT r.rental_id, r.user_id, r.vehicle_id, r.start_date, r.end_date,
               DATEDIFF(r.end_date, r.start_date) AS total_days,
               (DATEDIFF(r.end_date, r.start_date) * v.price_per_day) AS total_price
        FROM Rental r
        JOIN Vehicle v ON v.vehicle_id = r.vehicle_id
        WHERE r.rental_id = :rid
        """,
        {"rid": rental_id},
    )

    return RentalResponse(**dict(row))

# =========================================================
# Static Files - Mount last to avoid route conflicts
# =========================================================

# Serve static files (simple UI demo)
app.mount("/static", StaticFiles(directory="static"), name="static")