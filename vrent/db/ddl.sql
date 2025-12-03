START TRANSACTION;

-- =========================================================
-- User Table
-- =========================================================
-- Stores customer information for the vehicle rental system.
-- Uses soft delete pattern (deleted_at) to maintain referential integrity.
-- =========================================================
CREATE TABLE IF NOT EXISTS User (
    user_id        INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    name           VARCHAR(100) NOT NULL,                   -- Full name of the user
    email          VARCHAR(255) NOT NULL UNIQUE,            -- Unique email for login and communication
    phone          VARCHAR(20)  NOT NULL UNIQUE,            -- Contact number, must be unique
    password_hash  VARCHAR(255) NOT NULL,                   -- Hashed password (bcrypt/argon2 recommended)
    created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,  -- Account creation timestamp
    last_login_at  DATETIME NULL,                           -- Track user activity; NULL if never logged in
    deleted_at     DATETIME NULL,                           -- Soft delete: NULL = active, timestamp = deleted
    
    -- Enforce international phone format: optional +, then 7-15 digits
    CONSTRAINT chk_phone_format
        CHECK (phone REGEXP '^\\+?[0-9]{7,15}$'),
    
    -- Basic email validation to ensure proper format
    CONSTRAINT chk_email_format
        CHECK (email REGEXP '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$')
) ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4
COLLATE=utf8mb4_unicode_ci;

-- =========================================================
-- Vehicle Table
-- =========================================================
-- Catalog of rental vehicles with pricing and availability status.
-- Supports soft delete to preserve rental history integrity.
-- =========================================================
CREATE TABLE IF NOT EXISTS Vehicle (
    vehicle_id    INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    make          VARCHAR(50) NOT NULL,                    -- Manufacturer (e.g., Toyota, Ford)
    model         VARCHAR(50) NOT NULL,                    -- Model name (e.g., Camry, F-150)
    year          YEAR NOT NULL,                           -- Manufacturing year
    status        ENUM('available','rented','maintenance') NOT NULL DEFAULT 'available',  -- Current availability
    price_per_day DECIMAL(12,2) NOT NULL,                  -- Daily rental rate in currency units
    created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,  -- When vehicle was added to system
    deleted_at    DATETIME NULL,                           -- Soft delete: NULL = active
    
    -- Ensure rental price is always positive
    CONSTRAINT chk_price_positive
        CHECK (price_per_day > 0),
    
    -- Reasonable year range to prevent data entry errors
    CONSTRAINT chk_vehicle_year
        CHECK (year BETWEEN 1900 AND 2100)
) ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4
COLLATE=utf8mb4_unicode_ci;

-- Composite index for efficient vehicle search queries
-- Optimizes: "Find available vehicles by make/model"
CREATE INDEX idx_vehicle_status_make_model
    ON Vehicle (status, make, model);

-- =========================================================
-- Rental Table
-- =========================================================
-- Tracks vehicle rental transactions and booking history.
-- Maintains price snapshot at booking time for audit purposes.
-- Prevents double-booking through unique constraints.
-- =========================================================
CREATE TABLE IF NOT EXISTS Rental (
    rental_id        INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    user_id          INT UNSIGNED NOT NULL,               -- Customer who made the rental
    vehicle_id       INT UNSIGNED NOT NULL,               -- Vehicle being rented
    start_date       DATE NOT NULL,                       -- Rental period start (inclusive)
    end_date         DATE NOT NULL,                       -- Rental period end (inclusive)
    price_at_rental  DECIMAL(12,2) NOT NULL,              -- Daily rate locked at booking time
    total_cost       DECIMAL(12,2) NOT NULL,              -- Calculated total: price × duration
    created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,       -- When booking was made
    updated_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,  -- Last modification
    deleted_at       DATETIME NULL,                       -- Soft delete: NULL = active rental
    
    -- Ensure end date is not before start date
    CONSTRAINT chk_dates
        CHECK (end_date >= start_date),
    
    -- Redundant check for date logic (kept for explicit validation)
    CONSTRAINT chk_min_duration
        CHECK (DATEDIFF(end_date, start_date) >= 0),
    
    -- Enforce correct total cost calculation
    -- Formula: Inclusive date range, so always add 1 (e.g., Oct 15-20 = 6 days)
    CONSTRAINT chk_total_cost
        CHECK (
            total_cost = price_at_rental * (DATEDIFF(end_date, start_date) + 1)
        ),
    
    -- Foreign key: Link to user account (prevent deletion if active rentals exist)
    CONSTRAINT fk_rental_user
        FOREIGN KEY (user_id) REFERENCES User (user_id)
            ON DELETE RESTRICT ON UPDATE CASCADE,
    
    -- Foreign key: Link to vehicle (prevent deletion if active rentals exist)
    CONSTRAINT fk_rental_vehicle
        FOREIGN KEY (vehicle_id) REFERENCES Vehicle (vehicle_id)
            ON DELETE RESTRICT ON UPDATE CASCADE,
    
    -- Prevent double-booking: same vehicle cannot have overlapping rental periods
    CONSTRAINT uq_vehicle_date_overlap
        UNIQUE (vehicle_id, start_date, end_date)
) ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4
COLLATE=utf8mb4_unicode_ci;

-- Index for user rental history queries
-- Optimizes: "Show all rentals for a user, sorted by date"
CREATE INDEX idx_rental_user_start
    ON Rental (user_id, start_date);

-- Index for vehicle availability checks
-- Optimizes: "Find all rentals for a vehicle within a date range"
CREATE INDEX idx_rental_vehicle_dates
    ON Rental (vehicle_id, start_date, end_date);

COMMIT;
