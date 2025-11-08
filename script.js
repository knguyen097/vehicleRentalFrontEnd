const API = '';

const els =
{
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
    resetBtn: document.getElementById('resetBtn')
};

let state =
{
    limit: 12,
    offset: 0,
    total: 0,
    get page()
    {
        return Math.floor(this.offset / this.limit) + 1;
    },
    get totalPages()
    {
        return Math.max(1, Math.ceil(this.total / this.limit));
    }
};

function buildQuery({ forCount = false } = {})
{
    const q = new URLSearchParams();

    if (els.status.value) q.set('status', els.status.value);
    if (els.make.value) q.set('make', els.make.value.trim());
    if (els.model.value) q.set('model', els.model.value.trim());
    if (els.yearFrom.value) q.set('year_from', els.yearFrom.value);
    if (els.yearTo.value) q.set('year_to', els.yearTo.value);
    if (els.minPrice.value) q.set('min_price', els.minPrice.value);
    if (els.maxPrice.value) q.set('max_price', els.maxPrice.value);
    if (els.search.value.trim()) q.set('search', els.search.value.trim());

    if (!forCount)
    {
        q.set('sort_by', els.sortBy.value || 'created_at');
        q.set('sort_dir', els.sortDir.value || 'desc');
        q.set('limit', state.limit);
        q.set('offset', state.offset);
    }

    return q;
}

async function fetchTotal()
{
    const res = await fetch(`${API}/vehicles/count?${buildQuery({ forCount: true }).toString()}`);
    if (!res.ok)
    {
        state.total = 0;
        return;
    }
    const data = await res.json();
    state.total = data.count ?? 0;
}

async function fetchVehicles()
{
    const res = await fetch(`${API}/vehicles?${buildQuery().toString()}`);
    els.resultCount.textContent = 'Loading…';

    if (!res.ok)
    {
        els.grid.innerHTML = `<div class="muted">Failed to load vehicles (status ${res.status}).</div>`;
        els.resultCount.textContent = 'Error';
        updatePager();
        return;
    }

    const data = await res.json();
    renderVehicles(data);
    els.resultCount.textContent = `${data.length} result${data.length === 1 ? '' : 's'} on this page`;
    updatePager();
}

function renderVehicles(list)
{
    if (!list.length)
    {
        els.grid.innerHTML = `<div class="muted">No vehicles found. Try relaxing filters.</div>`;
        return;
    }

    els.grid.innerHTML = list.map(v =>
    {
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
                        <button class="btn primary">Rent Now</button>
                        <button class="btn">Details</button>
                    </div>
                </div>
            </article>
        `;
    }).join('');
}

function updatePager()
{
    els.pageInfo.textContent = `Page ${state.page} of ${state.totalPages}`;
    els.prevPage.disabled = state.page <= 1;
    els.nextPage.disabled = state.page >= state.totalPages;
}

function resetFilters()
{
    els.search.value = '';
    els.status.value = '';
    els.make.value = '';
    els.model.value = '';
    els.yearFrom.value = '';
    els.yearTo.value = '';
    els.minPrice.value = '';
    els.maxPrice.value = '';
    els.sortBy.value = 'created_at';
    els.sortDir.value = 'desc';
    state.offset = 0;
    load();
}

if (els.applyBtn) els.applyBtn.addEventListener('click', () =>
{
    state.offset = 0;
    load();
});

if (els.resetBtn) els.resetBtn.addEventListener('click', resetFilters);

if (els.search) els.search.addEventListener('input', () =>
{
    state.offset = 0;
    load();
});

if (els.prevPage) els.prevPage.addEventListener('click', () =>
{
    state.offset = Math.max(0, state.offset - state.limit);
    load();
});

if (els.nextPage) els.nextPage.addEventListener('click', () =>
{
    state.offset = Math.min((state.totalPages - 1) * state.limit, state.offset + state.limit);
    load();
});

async function load()
{
    await fetchTotal();
    await fetchVehicles();
}

load();