# Vehicle Rental API

FastAPI backend for vehicle rental management with MariaDB. Built for frontend developers—comprehensive React/JS integration examples included.

## Quick Start

**Start services:**
```bash
docker compose up -d
```

**Key URLs:**
- 🚀 API: http://localhost:8000
- 📚 API Docs (interactive): http://localhost:8000/docs
- 🎨 Demo UI: http://localhost:8000/static/index.html
- 🗄️ phpMyAdmin: http://localhost:8080

**Run tests:**
```bash
docker exec -it fastapi pytest /app/test_main.py -v
```

**Stop/restart:**
```bash
docker compose down                                      # Stop
docker compose down && docker volume rm vrent_db_data   # Reset database
docker compose up -d                                     # Start fresh
```

## Project layout

```
.
├── app/
│   ├── main.py           # FastAPI application
│   ├── requirements.txt  # Python dependencies
│   ├── test_main.py      # Test suite (60 tests)
│   └── static/
│       └── index.html    # Demo UI
├── db/
│   ├── ddl.sql          # Database schema
│   └── dml.sql          # Sample data
├── docker-compose.yml   # Services config
└── README.md
```

## API Endpoints

**📖 Full docs:** http://localhost:8000/docs (interactive Swagger UI)  
**🔗 OpenAPI schema:** http://localhost:8000/openapi.json

### Available Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check (returns API + DB status) |
| `GET` | `/vehicles` | List/filter vehicles with advanced search |
| `POST` | `/auth/register` | Create new user account |
| `POST` | `/auth/login` | Authenticate user |
| `GET` | `/rentals` | List all rentals (filterable) |
| `GET` | `/rentals/{id}` | Get single rental details |
| `GET` | `/users/{user_id}/rentals` | Get user's rental history |
| `POST` | `/rentals` | Create new rental booking |
| `PUT` | `/rentals/{id}` | Update rental dates |
| `DELETE` | `/rentals/{id}` | Cancel rental (soft delete) |

**Prototype UI:** http://localhost:8000/static/index.html

---

## Frontend Integration (React/JS)

**Base URL (dev):** `http://localhost:8000`  
**CORS:** Enabled for all origins (restrict in production)

### TypeScript Interfaces

```ts
export interface Vehicle {
  vehicle_id: number;
  make: string;
  model: string;
  year: number;
  status: 'available' | 'rented' | 'maintenance';
  price_per_day: number;
  created_at: string; // ISO timestamp
}

export interface AuthResponse {
  success: boolean;
  message: string;
  user_id?: number;
  name?: string;
  email?: string;
}

export interface Rental {
  rental_id: number;
  user_id: number;
  vehicle_id: number;
  start_date: string; // YYYY-MM-DD
  end_date: string;   // YYYY-MM-DD
  total_days: number;
  total_price: number;
}
```

---

## For Frontend Developers

**Base URL:** `http://localhost:8000` (CORS enabled for all origins in dev)  
**Tech Stack:** FastAPI + MariaDB + Docker  
**What you get:** RESTful API with filtering, pagination, auth, and rental management

### Query Parameter Helper

```ts
const API_BASE = 'http://localhost:8000';

function buildQueryParams(params: Record<string, any>): string {
  const searchParams = new URLSearchParams();
  
  Object.entries(params).forEach(([key, value]) => {
    // Skip null, undefined, and empty strings
    if (value === null || value === undefined || value === '') return;
    searchParams.append(key, String(value));
  });
  
  return searchParams.toString();
}

// Usage examples
export async function searchVehicles(filters: {
  status?: 'available' | 'rented' | 'maintenance';
  make?: string;
  model?: string;
  year_from?: number;
  year_to?: number;
  min_price?: number;
  max_price?: number;
  sort_by?: 'price' | 'year' | 'created_at';
  sort_dir?: 'asc' | 'desc';
  limit?: number;
  offset?: number;
}) {
  const qs = buildQueryParams(filters);
  const url = `${API_BASE}/vehicles${qs ? `?${qs}` : ''}`;
  
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
  
  return (await res.json()) as Vehicle[];
}
```

### Understanding FastAPI Query Filters

The `/vehicles` endpoint supports **11 optional query parameters** that combine with **AND logic**. All filters are optional—omit any you don't need.

**Available Filters:**

| Parameter | Type | Constraint | Example | Description |
|-----------|------|------------|---------|-------------|
| `status` | `string` | Enum: `available`, `rented`, `maintenance` | `?status=available` | Vehicle availability status |
| `make` | `string` | - | `?make=Toyota` | Manufacturer (case-sensitive) |
| `model` | `string` | - | `?model=Camry` | Model name (case-sensitive) |
| `year_from` | `number` | 1900-2100 | `?year_from=2020` | Min year (inclusive) |
| `year_to` | `number` | 1900-2100 | `?year_to=2024` | Max year (inclusive) |
| `min_price` | `number` | ≥ 0 | `?min_price=25.00` | Min daily price (inclusive) |
| `max_price` | `number` | ≥ 0 | `?max_price=100.00` | Max daily price (inclusive) |
| `sort_by` | `string` | Enum: `price`, `year`, `created_at` | `?sort_by=price` | Sort field (default: `created_at`) |
| `sort_dir` | `string` | Enum: `asc`, `desc` | `?sort_dir=asc` | Sort direction (default: `asc`) |
| `limit` | `number` | 1-100 | `?limit=20` | Results per page (default: 20) |
| `offset` | `number` | ≥ 0 | `?offset=40` | Skip N results (default: 0) |

**How Filters Work:**
- **Combine filters** by adding multiple query params: `?status=available&make=Toyota&year_from=2020`
- **Range filters** use both bounds: `?year_from=2020&year_to=2024` (vehicles from 2020-2024)
- **Empty/null values** are ignored automatically (won't affect query)
- **Invalid values** return HTTP 422 with validation details

### Complex Query Examples

**Example 1: Multi-filter vehicle search**

```ts
// Find affordable available Toyotas from 2020+, sorted by price
const vehicles = await searchVehicles({
  status: 'available',
  make: 'Toyota',
  year_from: 2020,
  max_price: 60,
  sort_by: 'price',
  sort_dir: 'asc',
  limit: 10
});

// Resulting URL:
// /vehicles?status=available&make=Toyota&year_from=2020&max_price=60&sort_by=price&sort_dir=asc&limit=10
```

**Example 2: Price range search**

```ts
// Vehicles between $30-$70/day, newest first
const vehicles = await searchVehicles({
  min_price: 30,
  max_price: 70,
  sort_by: 'year',
  sort_dir: 'desc'
});

// URL: /vehicles?min_price=30&max_price=70&sort_by=year&sort_dir=desc
```

**Example 3: Year range with status**

```ts
// Available vehicles from 2018-2022
const vehicles = await searchVehicles({
  status: 'available',
  year_from: 2018,
  year_to: 2022
});

// URL: /vehicles?status=available&year_from=2018&year_to=2022
```

**Example 4: Specific make and model**

```ts
// All Honda Civics (any status, any year)
const vehicles = await searchVehicles({
  make: 'Honda',
  model: 'Civic',
  sort_by: 'price',
  sort_dir: 'asc'
});

// URL: /vehicles?make=Honda&model=Civic&sort_by=price&sort_dir=asc
```

**Example 5: Budget-friendly search**

```ts
// Cheapest available vehicles under $50/day
const vehicles = await searchVehicles({
  status: 'available',
  max_price: 50,
  sort_by: 'price',
  sort_dir: 'asc',
  limit: 5
});

// URL: /vehicles?status=available&max_price=50&sort_by=price&sort_dir=asc&limit=5
```

**Pagination pattern:**

```ts
function VehicleList() {
  const [page, setPage] = useState(0);
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const pageSize = 20;

  useEffect(() => {
    searchVehicles({
      status: 'available',
      limit: pageSize,
      offset: page * pageSize
    }).then(setVehicles);
  }, [page]);

  return (
    <>
      {/* render vehicles */}
      <button onClick={() => setPage(p => p - 1)} disabled={page === 0}>
        Previous
      </button>
      <button onClick={() => setPage(p => p + 1)}>
        Next
      </button>
    </>
  );
}
```

**Dynamic filter builder with all options:**

```ts
function VehicleSearch() {
  const [filters, setFilters] = useState({
    status: '',
    make: '',
    model: '',
    year_from: '',
    year_to: '',
    min_price: '',
    max_price: '',
    sort_by: 'created_at',
    sort_dir: 'asc',
    limit: 20
  });
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [loading, setLoading] = useState(false);

  const handleSearch = async () => {
    setLoading(true);
    try {
      // buildQueryParams automatically filters empty strings
      const results = await searchVehicles(filters);
      setVehicles(results);
    } catch (error) {
      console.error('Search failed:', error);
    } finally {
      setLoading(false);
    }
  };

  // Auto-search when filters change (debounce in production)
  useEffect(() => {
    handleSearch();
  }, [filters]);

  return (
    <div>
      <form onSubmit={(e) => { e.preventDefault(); handleSearch(); }}>
        <div className="filters-grid">
          {/* Status filter */}
          <label>
            Status:
            <select 
              value={filters.status} 
              onChange={e => setFilters({...filters, status: e.target.value})}
            >
              <option value="">Any Status</option>
              <option value="available">Available</option>
              <option value="rented">Rented</option>
              <option value="maintenance">Maintenance</option>
            </select>
          </label>

          {/* Make filter */}
          <label>
            Make:
            <input 
              placeholder="e.g., Toyota" 
              value={filters.make}
              onChange={e => setFilters({...filters, make: e.target.value})}
            />
          </label>

          {/* Model filter */}
          <label>
            Model:
            <input 
              placeholder="e.g., Camry" 
              value={filters.model}
              onChange={e => setFilters({...filters, model: e.target.value})}
            />
          </label>

          {/* Year range */}
          <label>
            Year From:
            <input 
              type="number" 
              min="1900" 
              max="2100"
              placeholder="2020"
              value={filters.year_from}
              onChange={e => setFilters({...filters, year_from: e.target.value})}
            />
          </label>

          <label>
            Year To:
            <input 
              type="number" 
              min="1900" 
              max="2100"
              placeholder="2024"
              value={filters.year_to}
              onChange={e => setFilters({...filters, year_to: e.target.value})}
            />
          </label>

          {/* Price range */}
          <label>
            Min Price ($/day):
            <input 
              type="number" 
              min="0" 
              step="0.01"
              placeholder="25.00"
              value={filters.min_price}
              onChange={e => setFilters({...filters, min_price: e.target.value})}
            />
          </label>

          <label>
            Max Price ($/day):
            <input 
              type="number" 
              min="0" 
              step="0.01"
              placeholder="100.00"
              value={filters.max_price}
              onChange={e => setFilters({...filters, max_price: e.target.value})}
            />
          </label>

          {/* Sort options */}
          <label>
            Sort By:
            <select 
              value={filters.sort_by} 
              onChange={e => setFilters({...filters, sort_by: e.target.value})}
            >
              <option value="created_at">Date Added</option>
              <option value="price">Price</option>
              <option value="year">Year</option>
            </select>
          </label>

          <label>
            Direction:
            <select 
              value={filters.sort_dir} 
              onChange={e => setFilters({...filters, sort_dir: e.target.value})}
            >
              <option value="asc">Ascending</option>
              <option value="desc">Descending</option>
            </select>
          </label>

          {/* Results limit */}
          <label>
            Results:
            <select 
              value={filters.limit} 
              onChange={e => setFilters({...filters, limit: Number(e.target.value)})}
            >
              <option value="10">10</option>
              <option value="20">20</option>
              <option value="50">50</option>
              <option value="100">100</option>
            </select>
          </label>
        </div>

        <button type="submit" disabled={loading}>
          {loading ? 'Searching...' : 'Search Vehicles'}
        </button>

        {/* Clear all filters */}
        <button 
          type="button" 
          onClick={() => setFilters({
            status: '', make: '', model: '', year_from: '', year_to: '',
            min_price: '', max_price: '', sort_by: 'created_at', sort_dir: 'asc', limit: 20
          })}
        >
          Clear Filters
        </button>
      </form>

      {/* Results display */}
      <div className="results">
        <p>{vehicles.length} vehicle(s) found</p>
        {vehicles.map(v => (
          <div key={v.vehicle_id}>
            <h3>{v.make} {v.model} ({v.year})</h3>
            <p>Status: {v.status} | ${v.price_per_day}/day</p>
          </div>
        ))}
      </div>
    </div>
  );
}
```

**Testing filters via browser/Postman:**

```bash
# Simple status filter
curl "http://localhost:8000/vehicles?status=available"

# Combine multiple filters
curl "http://localhost:8000/vehicles?status=available&make=Toyota&max_price=60"

# Year and price range
curl "http://localhost:8000/vehicles?year_from=2020&year_to=2024&min_price=30&max_price=70"

# Sorted results
curl "http://localhost:8000/vehicles?sort_by=price&sort_dir=asc&limit=5"

# Complex query (available Toyotas, 2020+, under $60, cheapest first)
curl "http://localhost:8000/vehicles?status=available&make=Toyota&year_from=2020&max_price=60&sort_by=price&sort_dir=asc"
```

### Authentication Flow

```ts
// Register new user
async function register(name: string, email: string, phone: string, password: string) {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, email, phone, password })
  });

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || 'Registration failed');
  }

  const data: AuthResponse = await res.json();
  
  // Store auth state
  if (data.success && data.user_id) {
    localStorage.setItem('userId', String(data.user_id));
    localStorage.setItem('userName', data.name!);
    localStorage.setItem('userEmail', data.email!);
  }
  
  return data;
}

// Login
async function login(email: string, password: string) {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });

  if (res.status === 401) {
    throw new Error('Invalid email or password');
  }
  
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || 'Login failed');
  }

  const data: AuthResponse = await res.json();
  
  if (data.success && data.user_id) {
    localStorage.setItem('userId', String(data.user_id));
    localStorage.setItem('userName', data.name!);
    localStorage.setItem('userEmail', data.email!);
  }
  
  return data;
}

// React hook for auth state
function useAuth() {
  const [user, setUser] = useState<{ id: number; name: string; email: string } | null>(null);

  useEffect(() => {
    const userId = localStorage.getItem('userId');
    const userName = localStorage.getItem('userName');
    const userEmail = localStorage.getItem('userEmail');

    if (userId && userName && userEmail) {
      setUser({ id: Number(userId), name: userName, email: userEmail });
    }
  }, []);

  const logout = () => {
    localStorage.removeItem('userId');
    localStorage.removeItem('userName');
    localStorage.removeItem('userEmail');
    setUser(null);
  };

  return { user, logout };
}
```

### Rental Booking Flow

Complete example from vehicle selection to booking confirmation:

```ts
// 1. Search available vehicles
async function searchAvailableVehicles(startDate: string, endDate: string) {
  return searchVehicles({
    status: 'available',
    sort_by: 'price',
    sort_dir: 'asc'
  });
  // Note: Backend doesn't filter by date availability in /vehicles
  // You must check availability when creating rental
}

// 2. Create rental with conflict handling
async function createRental(
  userId: number,
  vehicleId: number,
  startDate: string,
  endDate: string
): Promise<Rental> {
  const res = await fetch(`${API_BASE}/rentals`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id: userId,
      vehicle_id: vehicleId,
      start_date: startDate,
      end_date: endDate
    })
  });

  if (res.status === 400) {
    // Date overlap conflict
    const error = await res.json();
    throw new Error(error.detail || 'Vehicle not available for selected dates');
  }

  if (res.status === 422) {
    // Invalid date range
    const error = await res.json();
    throw new Error(error.detail || 'Invalid date range');
  }

  if (res.status === 404) {
    throw new Error('Vehicle not found');
  }

  if (!res.ok) {
    throw new Error(`Booking failed: ${res.status}`);
  }

  return (await res.json()) as Rental;
}

// 3. React component example
function BookingForm({ vehicle }: { vehicle: Vehicle }) {
  const { user } = useAuth();
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [error, setError] = useState('');
  const [booking, setBooking] = useState<Rental | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!user) {
      setError('Please log in to book');
      return;
    }

    // Validate dates
    if (new Date(startDate) >= new Date(endDate)) {
      setError('End date must be after start date');
      return;
    }

    try {
      const rental = await createRental(user.id, vehicle.vehicle_id, startDate, endDate);
      setBooking(rental);
      alert(`Booking confirmed! Total: $${rental.total_price.toFixed(2)} for ${rental.total_days} days`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Booking failed');
    }
  };

  if (booking) {
    return (
      <div>
        <h3>Booking Confirmed!</h3>
        <p>Rental ID: {booking.rental_id}</p>
        <p>Duration: {booking.total_days} days</p>
        <p>Total: ${booking.total_price.toFixed(2)}</p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit}>
      <h3>Book {vehicle.make} {vehicle.model}</h3>
      <p>Price: ${vehicle.price_per_day}/day</p>
      
      <label>
        Start Date:
        <input 
          type="date" 
          value={startDate} 
          onChange={e => setStartDate(e.target.value)}
          min={new Date().toISOString().split('T')[0]}
          required
        />
      </label>
      
      <label>
        End Date:
        <input 
          type="date" 
          value={endDate} 
          onChange={e => setEndDate(e.target.value)}
          min={startDate || new Date().toISOString().split('T')[0]}
          required
        />
      </label>

      {error && <p style={{color: 'red'}}>{error}</p>}
      
      <button type="submit">Book Now</button>
    </form>
  );
}
```

### Rental Management

```ts
// Get user's rental history
async function getUserRentals(userId: number, page = 0, pageSize = 20) {
  const qs = buildQueryParams({
    limit: pageSize,
    skip: page * pageSize
  });
  
  const res = await fetch(`${API_BASE}/users/${userId}/rentals?${qs}`);
  if (!res.ok) throw new Error('Failed to load rentals');
  
  return (await res.json()) as Rental[];
}

// Cancel rental
async function cancelRental(rentalId: number) {
  const res = await fetch(`${API_BASE}/rentals/${rentalId}`, {
    method: 'DELETE'
  });

  if (res.status === 404) {
    throw new Error('Rental not found');
  }

  if (!res.ok) {
    throw new Error('Failed to cancel rental');
  }

  // 204 No Content - success
  return true;
}

// Update rental dates
async function updateRental(
  rentalId: number,
  userId: number,
  vehicleId: number,
  startDate: string,
  endDate: string
): Promise<Rental> {
  const res = await fetch(`${API_BASE}/rentals/${rentalId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id: userId,
      vehicle_id: vehicleId,
      start_date: startDate,
      end_date: endDate
    })
  });

  if (res.status === 400) {
    throw new Error('Vehicle not available for new dates');
  }

  if (res.status === 404) {
    throw new Error('Rental not found');
  }

  if (!res.ok) {
    throw new Error('Failed to update rental');
  }

  return (await res.json()) as Rental;
}
```

### Error Handling

Centralized error handler for common API responses:

```ts
async function apiCall<T>(
  url: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(url, options);

  // Success
  if (res.ok) {
    // 204 No Content
    if (res.status === 204) return undefined as T;
    return (await res.json()) as T;
  }

  // Parse error message
  let errorMessage = `HTTP ${res.status}`;
  try {
    const errorData = await res.json();
    errorMessage = errorData.detail || errorMessage;
  } catch {
    // Response not JSON
  }

  // Map status codes to user-friendly messages
  switch (res.status) {
    case 400:
      throw new Error(`Request error: ${errorMessage}`);
    case 401:
      throw new Error('Authentication failed. Please log in again.');
    case 404:
      throw new Error('Resource not found');
    case 422:
      throw new Error(`Validation error: ${errorMessage}`);
    case 500:
      throw new Error('Server error. Please try again later.');
    default:
      throw new Error(errorMessage);
  }
}

// Usage
try {
  const vehicles = await apiCall<Vehicle[]>(`${API_BASE}/vehicles?status=available`);
  console.log(vehicles);
} catch (error) {
  console.error(error.message); // User-friendly message
}
```

---
---

## Additional Resources

<details>
<summary><b>Database Access</b></summary>

**Connection details:**
- Host: `localhost:3306`
- Database: `dbname`
- User: `user`
- Password: `password`

**Connect via CLI:**
```bash
docker exec -it mariadb mysql -u user -p dbname
```

**phpMyAdmin:** http://localhost:8080

**Schema:** Auto-loaded from `db/ddl.sql` and `db/dml.sql` on first start
</details>

<details>
<summary><b>Dev Proxy Setup (Optional)</b></summary>

**Create React App:**
```json
// package.json
{
  "proxy": "http://localhost:8000"
}
```

**Vite:**
```ts
// vite.config.ts
export default defineConfig({
  server: {
    proxy: {
      '/vehicles': 'http://localhost:8000',
      '/auth': 'http://localhost:8000',
      '/rentals': 'http://localhost:8000'
    }
  }
});
```
</details>

<details>
<summary><b>TypeScript Type Generation</b></summary>

Generate types from OpenAPI schema:
```bash
npx openapi-typescript http://localhost:8000/openapi.json -o src/types/api.ts
```
</details>

<details>
<summary><b>Project Structure</b></summary>

```
.
├── app/
│   ├── main.py           # FastAPI application
│   ├── requirements.txt  # Python dependencies
│   ├── test_main.py      # Test suite (60 tests)
│   └── static/
│       └── index.html    # Demo UI
├── db/
│   ├── ddl.sql          # Database schema
│   └── dml.sql          # Sample data
├── docker-compose.yml   # Services config
└── README.md
```
</details>

---

**Need help?** Check `/docs` for interactive API exploration or review the examples above.