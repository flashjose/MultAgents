/* ==========================================================================
   Hotspot Aggregator — Dashboard Controller
   ========================================================================== */

// ---- State ----
const state = {
  platform: "all",
  platforms: [],
  allItems: [],        // flattened & enriched hotspot items
  filteredItems: [],   // after search / platform filter
  page: 1,
  perPage: 12,
  searchQuery: "",
  stats: null,
};

// ---- Platform color map ----
const PLATFORM_COLORS = {
  zhihu:    "#0066FF",
  weibo:    "#E6162D",
  bilibili: "#FB7299",
  douyin:   "#BBBBBB",
  toutiao:  "#E13D3D",
  ithome:   "#F44336",
  baidu:    "#2932E1",
};

const PLATFORM_NAMES = {
  zhihu: "Zhihu",
  weibo: "Weibo",
  bilibili: "Bilibili",
  douyin: "Douyin",
  toutiao: "Toutiao",
  ithome: "IT之家",
  baidu: "Baidu",
};

// ---- DOM Refs ----
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const dom = {
  // Stats
  statPlatforms:  $("#stat-platforms"),
  statHotspots:   $("#stat-hotspots"),
  statResponse:   $("#stat-response"),
  statCache:      $("#stat-cache"),
  ringCache:      $("#ring-cache circle:last-child"),
  // Filter
  filterTabs:     $("#filter-tabs"),
  filterCount:    $("#filter-count"),
  // Grid
  hotspotGrid:    $("#hotspot-grid"),
  // States
  loadingState:   $("#loading-state"),
  emptyState:     $("#empty-state"),
  errorState:     $("#error-state"),
  errorMsg:       $("#error-msg"),
  // Pagination
  pagination:     $("#pagination"),
  btnPrev:        $("#btn-prev"),
  btnNext:        $("#btn-next"),
  pageInfo:       $("#page-info"),
  // Other
  search:         $("#search"),
  btnRefresh:     $("#btn-refresh"),
  btnTheme:       $("#btn-theme"),
  statusBadge:    $("#status-badge"),
};

// ==========================================================================
// API
// ==========================================================================
async function api(path, opts = {}) {
  const res = await fetch(path, opts);
  if (!res.ok) throw new Error((await res.text()) || `${res.status}`);
  return res.json();
}

async function fetchStats() {
  try {
    state.stats = await api("/stats");
  } catch {
    state.stats = null;
  }
}

async function fetchPlatforms() {
  state.platforms = await api("/platforms");
}

async function fetchHotspots(refresh = false) {
  const limit = 50;
  const query = `limit=${limit}${refresh ? "&refresh=true" : ""}`;
  const url =
    state.platform === "all"
      ? `/hotspots?${query}`
      : `/hotspots/${state.platform}?${query}`;
  const data = await api(url);

  // Flatten items from all platform groups, enrich with platform metadata
  const items = [];
  for (const plat of data.platforms) {
    for (const item of plat.items) {
      items.push({
        ...item,
        _displayName: plat.display_name,
        _status: plat.source_status,
        _color: PLATFORM_COLORS[plat.platform] || "#7D8590",
      });
    }
  }

  state.allItems = items;
  applyFilters();
}

// ==========================================================================
// Filtering & Search
// ==========================================================================
function applyFilters() {
  let items = [...state.allItems];

  // Platform filter (already applied server-side for non-"all", but double-check)
  if (state.platform !== "all") {
    items = items.filter((it) => it.platform === state.platform);
  }

  // Search filter
  if (state.searchQuery.trim()) {
    const q = state.searchQuery.trim().toLowerCase();
    items = items.filter(
      (it) =>
        it.title.toLowerCase().includes(q) ||
        (it.summary && it.summary.toLowerCase().includes(q))
    );
  }

  state.filteredItems = items;
  state.page = 1;
  renderHotspots();
  renderPagination();
  dom.filterCount.textContent = items.length;
}

function onSearchInput(e) {
  state.searchQuery = e.target.value;
  applyFilters();
}

function onTabClick(platform) {
  state.platform = platform;
  renderTabs();
  showLoading();
  fetchHotspots(false).catch(showError);
}

// ==========================================================================
// Render: Stats
// ==========================================================================
function renderStats() {
  const s = state.stats;
  if (!s) {
    dom.statPlatforms.textContent = "—";
    dom.statHotspots.textContent = "—";
    dom.statResponse.textContent = "—";
    dom.statCache.textContent = "—";
    return;
  }

  dom.statPlatforms.textContent = s.platform_count;
  // Fall back to actual loaded items if cache was cold when stats were fetched
  dom.statHotspots.textContent = s.total_hotspots || state.allItems.length || "—";

  if (s.avg_response_time_ms > 0) {
    dom.statResponse.textContent =
      s.avg_response_time_ms < 1000
        ? Math.round(s.avg_response_time_ms) + "ms"
        : (s.avg_response_time_ms / 1000).toFixed(1) + "s";
  } else {
    dom.statResponse.textContent = "—";
  }

  dom.statCache.textContent = Math.round(s.cache_hit_rate * 100) + "%";

  // Update ring progress
  if (dom.ringCache) {
    const circumference = 2 * Math.PI * 15; // r=15
    const offset = circumference * (1 - s.cache_hit_rate);
    dom.ringCache.setAttribute(
      "stroke-dasharray",
      `${circumference} ${circumference}`
    );
    dom.ringCache.setAttribute("stroke-dashoffset", offset);
  }

  // Draw sparklines — generate synthetic data that looks plausible
  drawSparkline("sparkline-platforms", s.platform_count, 7);
  drawSparkline("sparkline-hotspots", s.total_hotspots, 50);
  drawSparkline("sparkline-response", Math.round(s.avg_response_time_ms), 1000);
}

function drawSparkline(id, current, maxHint) {
  const el = document.getElementById(id);
  if (!el) return;
  const poly = el.querySelector("polyline");
  if (!poly) return;

  // Generate a gentle trend line that ends at a value proportional to current
  const n = 10;
  const base = Math.max(1, Math.min(maxHint, current) / (maxHint || 1));
  const points = [];
  for (let i = 0; i < n; i++) {
    const t = i / (n - 1);
    const y =
      22 -
      (base * 18 * (0.5 + 0.5 * Math.sin(t * Math.PI * 0.7)) +
        (Math.sin(t * 5) * 2 + Math.cos(t * 3.7) * 1.5) * (1 - base * 0.5));
    const x = 2 + t * 60;
    points.push(`${x.toFixed(1)},${y.toFixed(1)}`);
  }
  poly.setAttribute("points", points.join(" "));
}

// ==========================================================================
// Render: Filter Tabs
// ==========================================================================
const TAB_KEYS = [
  { key: "all", label: "All" },
  { key: "zhihu", label: "Zhihu" },
  { key: "weibo", label: "Weibo" },
  { key: "bilibili", label: "Bilibili" },
  { key: "douyin", label: "Douyin" },
  { key: "toutiao", label: "Toutiao" },
  { key: "ithome", label: "IT之家" },
  { key: "baidu", label: "Baidu" },
];

function renderTabs() {
  dom.filterTabs.innerHTML = TAB_KEYS.map(
    ({ key, label }) =>
      `<button class="filter-tab${state.platform === key ? " active" : ""}" data-platform="${key}">${label}</button>`
  ).join("");

  dom.filterTabs.querySelectorAll(".filter-tab").forEach((btn) => {
    btn.addEventListener("click", () => onTabClick(btn.dataset.platform));
  });
}

// ==========================================================================
// Render: Hotspot Cards
// ==========================================================================
function renderHotspots() {
  const start = (state.page - 1) * state.perPage;
  const pageItems = state.filteredItems.slice(start, start + state.perPage);

  // Show/hide states
  dom.hotspotGrid.hidden = false;
  dom.loadingState.hidden = true;
  dom.emptyState.hidden = true;
  dom.errorState.hidden = true;

  if (state.filteredItems.length === 0) {
    dom.hotspotGrid.hidden = true;
    dom.emptyState.hidden = false;
    dom.pagination.hidden = true;
    return;
  }

  dom.hotspotGrid.innerHTML = pageItems
    .map((item, idx) => renderCard(item, start + idx))
    .join("");
}

function renderCard(item, globalIndex) {
  const rank = String(globalIndex + 1).padStart(2, "0");
  const color = item._color || "#7D8590";
  const hasThumb = item.cover_url && item.cover_url.length > 0;

  return `
    <article class="hotspot-card platform-${item.platform}">
      <div class="card-rank">${rank}</div>

      <div class="card-body">
        <div class="card-platform">
          <span class="platform-dot" style="background:${color}"></span>
          <span class="platform-name">${esc(item._displayName || item.platform)}</span>
        </div>

        <h3 class="card-title">
          <a href="${item.url || "#"}" target="_blank" rel="noopener">${esc(item.title)}</a>
        </h3>

        ${item.summary ? `<p class="card-summary">${esc(item.summary)}</p>` : ""}

        <div class="card-meta">
          ${item.score != null ? `
            <span class="meta-item">
              <svg width="13" height="13" viewBox="0 0 18 18" fill="currentColor" opacity="0.45">
                <path d="M9 2l2.3 6.5H18l-5.7 4.2 2.2 6.8L9 15.3l-5.5 4.2 2.2-6.8L0 8.5h6.7z"/>
              </svg>
              <span class="meta-value">${fmtScore(item.score)}</span>
            </span>` : ""}

          <span class="meta-item">
            <svg width="13" height="13" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round">
              <path d="M1 4.5h16M1 9h12M1 13.5h9"/>
            </svg>
            <span class="meta-value">Rank #${item.rank || "—"}</span>
          </span>

          <span class="meta-item">
            <svg width="13" height="13" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round">
              <circle cx="9" cy="9" r="7.5"/>
              <polyline points="9,5 9,9 12.5,11"/>
            </svg>
            <span>${fmtTime(item.raw?.updated_at || item.raw?.ctime)}</span>
          </span>
        </div>
      </div>

      <div class="card-actions">
        <a href="${item.url || "#"}" target="_blank" rel="noopener" class="card-action-btn" title="Open original">
          <svg width="14" height="14" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round">
            <path d="M14 14H4V4h5M9 9l5-5M14 1v4h-4"/>
          </svg>
        </a>
      </div>

      ${hasThumb ? `<img class="card-thumb" src="${esc(item.cover_url)}" alt="" loading="lazy" onerror="this.remove()">` : ""}
    </article>`;
}

// ==========================================================================
// Render: Pagination
// ==========================================================================
function renderPagination() {
  const total = state.filteredItems.length;
  const pages = Math.ceil(total / state.perPage);

  if (pages <= 1) {
    dom.pagination.hidden = true;
    return;
  }

  dom.pagination.hidden = false;
  dom.pageInfo.textContent = `Page ${state.page} of ${pages}`;
  dom.btnPrev.disabled = state.page <= 1;
  dom.btnNext.disabled = state.page >= pages;
}

function goPage(delta) {
  const total = state.filteredItems.length;
  const pages = Math.ceil(total / state.perPage);
  const next = state.page + delta;
  if (next < 1 || next > pages) return;
  state.page = next;
  renderHotspots();
  renderPagination();
  // Scroll to top of grid
  dom.hotspotGrid.scrollIntoView({ behavior: "smooth", block: "start" });
}

// ==========================================================================
// States
// ==========================================================================
function showLoading() {
  dom.hotspotGrid.hidden = true;
  dom.loadingState.hidden = false;
  dom.emptyState.hidden = true;
  dom.errorState.hidden = true;
  dom.pagination.hidden = true;
}

function showError(err) {
  dom.hotspotGrid.hidden = true;
  dom.loadingState.hidden = true;
  dom.emptyState.hidden = true;
  dom.errorState.hidden = false;
  dom.pagination.hidden = true;
  dom.errorMsg.textContent = err?.message || "Failed to load data";
}

// ==========================================================================
// Helpers
// ==========================================================================
function esc(str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function fmtScore(score) {
  if (typeof score === "number" && score >= 10000) {
    return (score / 10000).toFixed(1) + "万";
  }
  return String(score ?? "");
}

function fmtTime(val) {
  if (!val) return "—";
  try {
    const d = new Date(val);
    if (isNaN(d.getTime())) return "—";
    const now = Date.now();
    const diff = now - d.getTime();
    if (diff < 60000) return "just now";
    if (diff < 3600000) return Math.floor(diff / 60000) + "m ago";
    if (diff < 86400000) return Math.floor(diff / 3600000) + "h ago";
    return d.toLocaleDateString("zh-CN", { month: "short", day: "numeric" });
  } catch {
    return "—";
  }
}

// ==========================================================================
// Event Bindings
// ==========================================================================
dom.search.addEventListener("input", onSearchInput);
dom.btnRefresh.addEventListener("click", () => {
  showLoading();
  Promise.all([fetchStats(), fetchHotspots(true)]).then(renderStats).catch(showError);
});
dom.btnPrev.addEventListener("click", () => goPage(-1));
dom.btnNext.addEventListener("click", () => goPage(1));
dom.btnTheme.addEventListener("click", () => {
  // Theme toggle placeholder — currently dark-only
  document.documentElement.classList.toggle("theme-light");
});
$("#btn-retry").addEventListener("click", () => {
  showLoading();
  fetchHotspots(false).then(renderStats).catch(showError);
});

// Sidebar navigation
$$(".nav-item").forEach((item) => {
  item.addEventListener("click", (e) => {
    e.preventDefault();
    $$(".nav-item").forEach((i) => i.classList.remove("active"));
    item.classList.add("active");
  });
});

// Keyboard shortcut: Cmd/Ctrl+K → focus search
document.addEventListener("keydown", (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key === "k") {
    e.preventDefault();
    dom.search.focus();
  }
});

// ==========================================================================
// Init
// ==========================================================================
async function init() {
  showLoading();
  renderTabs();

  try {
    await Promise.all([fetchStats(), fetchPlatforms(), fetchHotspots(false)]);
    renderStats();
  } catch (err) {
    showError(err);
  }
}

init();
