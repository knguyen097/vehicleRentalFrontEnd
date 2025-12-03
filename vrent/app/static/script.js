const API = 'http://localhost:8000';
const STORAGE_KEY = 'currentUser';

const els = {
    grid: document.getElementById('grid'),
    resultCount: document.getElementById('resultCount'),
    prevPage: document.getElementById('prevPage'),
    nextPage: document.getElementById('nextPage'),
    pageInfo: document.getElementById('pageInfo'),
    search: document.getElementById('searchInput'),
    status: document.getElementById('statusSelect'),
    make: document.getElementById('makeInput'),
    model: document.getElementById('modelInput'),
    yearFrom: document.getElementById('yearFrom'),
    yearTo: document.getElementById('yearTo'),
    minPrice: document.getElementById('minPrice'),
    maxPrice: document.getElementById('maxPrice'),
    sortBy: document.getElementById('sortBy'),
    sortDir: document.getElementById('sortDir'),
    applyBtn: document.getElementById('applyBtn'),
    resetBtn: document.getElementById('resetBtn'),
    signInBtn: document.getElementById('signInBtn'),
    userMenu: document.querySelector('.user-menu'),
    userDropdown: document.getElementById('userDropdown'),
    myRentalsBtn: document.getElementById('myRentalsBtn'),
    signOutBtn: document.getElementById('signOutBtn')
};

// Pagination state: 12 per page
const state = {
    page: 1,
    limit: 12,
    offset: 0,
    total: 0
};

// Helper: total pages (>= 1)
function getTotalPages() {
    return Math.max(1, Math.ceil(state.total / state.limit));
}

// --- auth helpers -----------------------------------------------------------

function getCurrentUser() {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    try { return JSON.parse(raw); }
    catch { return null; }
}

function clearCurrentUser() {
    localStorage.removeItem(STORAGE_KEY);
}

function updateSignInUI() {
    if (!els.signInBtn) return;
    const user = getCurrentUser();

    if (user && user.name) {
        const first = user.name.split(' ')[0];
        els.signInBtn.textContent = `Hi, ${first}`;
        els.signInBtn.classList.add('is-user');
        if (els.userMenu) els.userMenu.classList.add('is-logged-in');
    } else {
        els.signInBtn.textContent = 'Sign In';
        els.signInBtn.classList.remove('is-user');
        if (els.userMenu) els.userMenu.classList.remove('is-logged-in');
    }
}

// --- query + API calls ------------------------------------------------------

function buildQuery({ forCount = false } = {}) {
    const q = new URLSearchParams();

    if (els.status?.value) q.set('status', els.status.value);
    if (els.make?.value) q.set('make', els.make.value);
    if (els.model?.value) q.set('model', els.model.value);
    if (els.yearFrom?.value) q.set('year_from', els.yearFrom.value);
    if (els.yearTo?.value) q.set('year_to', els.yearTo.value);
    if (els.minPrice?.value) q.set('min_price', els.minPrice.value);
    if (els.maxPrice?.value) q.set('max_price', els.maxPrice.value);
    if (els.search?.value.trim()) q.set('search', els.search.value.trim());

    if (!forCount) {
        if (els.sortBy) q.set('sort_by', els.sortBy.value || 'created_at');
        if (els.sortDir) q.set('sort_dir', els.sortDir.value || 'desc');
        q.set('limit', state.limit);
        q.set('offset', state.offset);
    }

    return q;
}

async function fetchTotal() {
    const res = await fetch(`${API}/vehicles/count?${buildQuery({ forCount: true })}`);
    if (!res.ok) {
        state.total = 0;
        return;
    }
    const data = await res.json();

    // Backend returns { total: number }
    state.total = data.total ?? 0;
}



async function fetchVehicles() {
    const res = await fetch(`${API}/vehicles?${buildQuery()}`);
    els.resultCount.textContent = "Loading…";

    if (!res.ok) {
        els.grid.innerHTML = `<div class="muted">Failed to load vehicles.</div>`;
        return;
    }

    const vehicles = await res.json();
    renderVehicles(vehicles);

    els.resultCount.textContent = `${vehicles.length} results on this page`;
    updatePager();
}


function renderVehicles(list) {
    if (!els.grid) return;

    if (!list.length) {
        els.grid.innerHTML = `<div class="muted">No vehicles found. Try relaxing filters.</div>`;
        return;
    }

    els.grid.innerHTML = list.map(v => {
        const title = `${v.make} ${v.model}`.trim();
        const badge = `<span class="badge">${v.status || '—'}</span>`;
        return `
            <article class="card">
                <div class="media"><span>${title}</span></div>
                <div class="body">
                    <h3>${title}</h3>
                    <div class="kv">
                        <span>Year: <strong>${v.year ?? '—'}</strong></span>
                        <span>Price: <strong class="price">$${Number(v.price_per_day ?? 0).toFixed(2)}</strong>/day</span>
                        ${badge}
                    </div>
                    <div class="actions">
                        <button class="btn primary rent-btn" data-id="${v.vehicle_id}">Rent Now</button>
                    </div>
                </div>
            </article>
        `;
    }).join('');
}

function updatePager() {
    if (!els.pageInfo) return;
    const totalPages = getTotalPages();
    els.pageInfo.textContent = `Page ${state.page} of ${totalPages}`;

    if (els.prevPage) els.prevPage.disabled = state.page <= 1;
    if (els.nextPage) els.nextPage.disabled = state.page >= totalPages;
}

function resetFilters() {
    if (els.search) els.search.value = '';
    if (els.status) els.status.value = '';
    if (els.make) els.make.value = '';
    if (els.model) els.model.value = '';
    if (els.yearFrom) els.yearFrom.value = '';
    if (els.yearTo) els.yearTo.value = '';
    if (els.minPrice) els.minPrice.value = '';
    if (els.maxPrice) els.maxPrice.value = '';
    if (els.sortBy) els.sortBy.value = 'created_at';
    if (els.sortDir) els.sortDir.value = 'desc';

    state.page = 1;
    state.offset = 0;
}

// --- UI event wiring --------------------------------------------------------

if (els.applyBtn) els.applyBtn.addEventListener('click', () => {
    state.page = 1;
    state.offset = 0;
    fetchTotal().then(fetchVehicles);
});

if (els.resetBtn) els.resetBtn.addEventListener('click', () => {
    resetFilters();
    fetchTotal().then(fetchVehicles);
});

if (els.search) els.search.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        e.preventDefault();
        state.page = 1;
        state.offset = 0;
        fetchTotal().then(fetchVehicles);
    }
});

if (els.prevPage) els.prevPage.addEventListener('click', () => {
    if (state.page > 1) {
        state.page--;
        state.offset = (state.page - 1) * state.limit;
        fetchTotal().then(fetchVehicles);
    }
});

if (els.nextPage) els.nextPage.addEventListener('click', () => {
    const totalPages = getTotalPages();
    if (state.page < totalPages) {
        state.page++;
        state.offset = (state.page - 1) * state.limit;
        fetchTotal().then(fetchVehicles);
    }
});

// Sign in button behaviour
if (els.signInBtn) {
    els.signInBtn.addEventListener('click', () => {
        const user = getCurrentUser();
        if (!user) {
            window.location.href = './login.html';
        }
        // if logged in, dropdown is handled by hover
    });
}

// Dropdown: My Rentals
if (els.myRentalsBtn) {
    els.myRentalsBtn.addEventListener('click', () => {
        const user = getCurrentUser();
        if (!user) {
            window.location.href = './login.html';
            return;
        }
        window.location.href = './rentals.html';
    });
}

// Dropdown: Sign Out
if (els.signOutBtn) {
    els.signOutBtn.addEventListener('click', () => {
        clearCurrentUser();
        updateSignInUI();
    });
}

// Global click handler for Rent Now
document.addEventListener('click', async (event) => {
    const rentBtn = event.target.closest('.rent-btn');
    if (!rentBtn) return;

    const vehicleId = Number(rentBtn.dataset.id);
    const user = getCurrentUser();
    if (!user) {
        alert('Please sign in before renting a vehicle.');
        window.location.href = './login.html';
        return;
    }

    const originalText = rentBtn.textContent;
    rentBtn.disabled = true;
    rentBtn.textContent = 'Booking…';

    // simple default: today → tomorrow
    const today = new Date();
    const startDate = today.toISOString().slice(0, 10);
    const tomorrow = new Date(today);
    tomorrow.setDate(today.getDate() + 1);
    const endDate = tomorrow.toISOString().slice(0, 10);

    try {
        const res = await fetch(`${API}/rentals`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                vehicle_id: vehicleId,
                user_id: user.user_id,
                start_date: startDate,
                end_date: endDate,
            }),
        });

        const raw = await res.text();
        let data = null;
        try {
            data = raw ? JSON.parse(raw) : null;
        } catch {
            // ignore JSON parse failure
        }

        if (!res.ok) {
            const msg =
                (data && (data.detail || data.message)) ||
                raw ||
                'Failed to rent vehicle.';
            throw new Error(msg);
        }

        alert((data && data.message) || 'Rental created successfully!');
        await fetchTotal();
        await fetchVehicles();
    } catch (err) {
        alert(err.message || 'Something went wrong while booking.');
    } finally {
        rentBtn.disabled = false;
        rentBtn.textContent = originalText;
    }
});

// --- initial load -----------------------------------------------------------

async function load() {
    updateSignInUI();
    await fetchTotal();
    await fetchVehicles();
}

load();