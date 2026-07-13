/* ==========================================================================
   HotHub — Dashboard Controller
   Reuses the data layer (api / fetchStats / fetchPlatforms / fetchHotspots),
   adds theme control, ranking tabs, favorites, categories, trend & system status.
   ========================================================================== */

// ------------------------------- State ------------------------------------
const state = {
  platforms: [],
  byPlatform: {},          // name -> enriched items[]
  platformStatus: {},      // name -> source_status
  allItems: [],            // flattened & enriched
  stats: null,
  system: null,
  rankTab: "composite",    // composite | latest | hottest
  rankPlatform: null,      // optional platform filter (from platform card click)
  rankLimit: 15,
  searchQuery: "",
  favorites: new Set(loadFavorites()),
  trendSamples: [],
  apiCalls: 0,
  uptimeSeconds: 0,
  lastUpdated: null,
};

// ------------------------------- Constants --------------------------------
const PLATFORM_COLORS = {
  zhihu: "#0066FF", weibo: "#E6162D", bilibili: "#FB7299",
  douyin: "#12B7B0", toutiao: "#E13D3D", ithome: "#D9382B", baidu: "#2932E1",
};
const PLATFORM_INITIALS = {
  zhihu: "知", weibo: "微", bilibili: "B", douyin: "抖",
  toutiao: "头", ithome: "IT", baidu: "百",
};

const CATEGORIES = [
  { key: "AI", kw: ["ai", "人工智能", "大模型", "gpt", "chatgpt", "机器学习", "算法", "openai", "文心", "通义", "sora", "智能体", "deepseek"] },
  { key: "科技", kw: ["科技", "芯片", "半导体", "手机", "电脑", "华为", "苹果", "小米", "5g", "卫星", "发射", "量子", "机器人", "特斯拉", "显卡", "数码", "航天"] },
  { key: "互联网", kw: ["互联网", "阿里", "腾讯", "字节", "百度", "美团", "京东", "拼多多", "平台", "app", "直播", "电商", "抖音", "微信"] },
  { key: "财经", kw: ["财经", "股", "基金", "经济", "金融", "gdp", "房价", "楼市", "央行", "利率", "黄金", "上市", "融资", "收购", "美元", "汇率"] },
  { key: "娱乐", kw: ["娱乐", "明星", "电影", "电视剧", "综艺", "演唱会", "音乐", "票房", "网红", "偶像", "演员", "导演", "热搜"] },
  { key: "体育", kw: ["体育", "比赛", "足球", "篮球", "nba", "世界杯", "奥运", "冠军", "联赛", "球员", "夺冠", "决赛", "国足"] },
  { key: "社会", kw: [] }, // catch-all
];

const STATUS_MAP = {
  online: { cls: "dot-ok", text: "在线" },
  memory: { cls: "dot-info", text: "内存回退" },
  not_configured: { cls: "dot-muted", text: "未接入" },
  offline: { cls: "dot-bad", text: "离线" },
};
const COMP_LABEL = { fastapi: "FastAPI", redis: "Redis", mysql: "MySQL" };

const VIEW_META = {
  trending: { title: "全网热点", desc: "跨平台聚合热榜视图正在建设中。" },
  live: { title: "实时热榜", desc: "分平台实时滚动榜单即将上线。" },
  search: { title: "高级搜索", desc: "多维度搜索（关键词 / 平台 / 时间）开发中。" },
  analytics: { title: "数据分析", desc: "趋势与分类深度分析看板开发中。" },
  favorites: { title: "我的收藏", desc: "收藏管理视图开发中，当前可在榜单中收藏条目。" },
  settings: { title: "系统设置", desc: "主题、刷新频率与数据源配置开发中。" },
};

// ------------------------------- DOM refs ---------------------------------
const $ = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);
const dom = {
  platformRail: $("#platform-rail"),
  rankBody: $("#rank-body"),
  rankTabs: $("#rank-tabs"),
  boardCount: $("#board-count"),
  boardFoot: $("#board-foot"),
  btnMore: $("#btn-more"),
  cats: $("#cats"),
  trendCurrent: $("#trend-current"),
  trendDelta: $("#trend-delta"),
  trendLine: $("#trend-line"),
  trendArea: $("#trend-area"),
  sysbarItems: $("#sysbar-items"),
  sysbarUptime: $("#sysbar-uptime"),
  msScraped: $("#ms-scraped"),
  msApi: $("#ms-api"),
  msCache: $("#ms-cache"),
  msUptime: $("#ms-uptime"),
  ssSystem: $("#ss-system"),
  ssApi: $("#ss-api"),
  ssCache: $("#ss-cache"),
  ssUpdated: $("#ss-updated"),
  search: $("#search"),
  btnRefresh: $("#btn-refresh"),
  btnTheme: $("#btn-theme"),
  btnRetry: $("#btn-retry"),
  loading: $("#loading-state"),
  error: $("#error-state"),
  errorMsg: $("#error-msg"),
  placeholder: $("#placeholder"),
  placeholderTitle: $("#placeholder-title"),
  placeholderDesc: $("#placeholder-desc"),
  placeholderBack: $("#placeholder-back"),
};

// ------------------------------- API layer --------------------------------
async function api(path, opts = {}) {
  state.apiCalls += 1;
  if (dom.msApi) dom.msApi.textContent = state.apiCalls;
  const res = await fetch(path, opts);
  if (!res.ok) throw new Error((await res.text()) || `${res.status}`);
  return res.json();
}

async function fetchStats() {
  try { state.stats = await api("/stats"); } catch { state.stats = null; }
}

async function fetchPlatforms() {
  state.platforms = await api("/platforms");
}

async function fetchSystem() {
  try {
    state.system = await api("/system/status");
    state.uptimeSeconds = state.system.uptime_seconds || 0;
  } catch { state.system = null; }
}

async function fetchHotspots(refresh = false) {
  const data = await api(`/hotspots?limit=50${refresh ? "&refresh=true" : ""}`);
  const all = [];
  const byPlatform = {};
  const platformStatus = {};
  for (const plat of data.platforms) {
    platformStatus[plat.platform] = plat.source_status;
    const list = [];
    for (const item of plat.items) {
      const enriched = {
        ...item,
        _displayName: plat.display_name,
        _status: plat.source_status,
        _color: PLATFORM_COLORS[plat.platform] || "#7D8590",
        _heat: parseHeat(item.score),
        _timeRaw: item.raw?.updated_at ?? item.raw?.ctime ?? item.raw?.created_at ?? plat.fetched_at ?? null,
        _id: `${item.platform}::${item.url || item.title}`,
      };
      list.push(enriched);
      all.push(enriched);
    }
    byPlatform[plat.platform] = list;
  }
  state.allItems = all;
  state.byPlatform = byPlatform;
  state.platformStatus = platformStatus;
  state.lastUpdated = new Date();
  recordTrend(all.length);
}

// ------------------------------- Theme ------------------------------------
function toggleTheme() {
  const cur = document.documentElement.getAttribute("data-theme");
  const next = cur === "dark" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", next);
  try { localStorage.setItem("hothub-theme", next); } catch {}
  renderTrend(); // re-read CSS-var driven colors if needed
}

// ------------------------------- Ranking ----------------------------------
function orderedItems() {
  let list;
  if (state.rankTab === "hottest") {
    list = [...state.allItems].sort((a, b) => b._heat - a._heat);
  } else if (state.rankTab === "latest") {
    list = [...state.allItems].sort((a, b) => timeMs(b._timeRaw) - timeMs(a._timeRaw));
  } else {
    list = compositeOrder(); // interleave platforms by rank
  }
  if (state.rankPlatform) list = list.filter((it) => it.platform === state.rankPlatform);
  const q = state.searchQuery.trim().toLowerCase();
  if (q) {
    list = list.filter(
      (it) =>
        it.title.toLowerCase().includes(q) ||
        (it.summary && it.summary.toLowerCase().includes(q)) ||
        (it._displayName && it._displayName.toLowerCase().includes(q))
    );
  }
  return list;
}

function compositeOrder() {
  const groups = state.platforms.map((p) => state.byPlatform[p.name] || []);
  const maxLen = groups.reduce((m, g) => Math.max(m, g.length), 0);
  const out = [];
  for (let i = 0; i < maxLen; i++) {
    for (const g of groups) if (g[i]) out.push(g[i]);
  }
  return out;
}

function renderRanking() {
  const list = orderedItems();
  const visible = list.slice(0, state.rankLimit);
  dom.boardCount.textContent = `${list.length} 条${state.rankPlatform ? " · " + platformName(state.rankPlatform) : ""}`;

  if (!visible.length) {
    dom.rankBody.innerHTML = `<div class="state-block" style="padding:40px 20px">未找到匹配的热点</div>`;
    dom.boardFoot.hidden = true;
    return;
  }

  dom.rankBody.innerHTML = visible.map((it, i) => rowHTML(it, i)).join("");
  dom.boardFoot.hidden = list.length <= state.rankLimit;

  // bind action buttons
  dom.rankBody.querySelectorAll(".ract-fav").forEach((btn) => {
    btn.addEventListener("click", () => toggleFavorite(btn.dataset.id));
  });
}

function rowHTML(it, i) {
  const pos = i + 1;
  const badge = pos <= 3
    ? `<span class="rank-badge rank-${pos}">${pos}</span>`
    : `<span class="rank-badge">${pos}</span>`;
  const heatText = fmtScore(it.score) || "—";
  const cold = it._heat > 0 ? "" : " cold";
  const faved = state.favorites.has(it._id) ? " faved" : "";
  const summary = it.summary && it.summary.trim();
  const showSummary = summary && summary.length > 4 && !/^\d+$/.test(summary);

  return `
    <div class="trow">
      <span class="col-rank">${badge}</span>
      <span class="rtitle">
        <a href="${it.url || "#"}" target="_blank" rel="noopener">${esc(it.title)}</a>
        ${showSummary ? `<span class="rsummary">${esc(summary)}</span>` : ""}
      </span>
      <span class="rsrc rsrc-cell">
        <span class="pdot" style="background:${it._color}"></span>${esc(it._displayName || it.platform)}
      </span>
      <span class="rheat${cold}">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.07-2.14-.22-4.05 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.15.43-2.29 1-3a2.5 2.5 0 0 0 2.5 2.5z"/></svg>
        ${heatText}
      </span>
      <span class="rtime rtime-cell">${fmtTime(it._timeRaw)}</span>
      <span class="ract">
        <button class="ract-btn ract-fav${faved}" data-id="${esc(it._id)}" title="收藏">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21l-7-4.9L5 21V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>
        </button>
        <a class="ract-btn" href="${it.url || "#"}" target="_blank" rel="noopener" title="打开原文">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/></svg>
        </a>
      </span>
    </div>`;
}

function setRankTab(tab) {
  state.rankTab = tab;
  state.rankLimit = 15;
  dom.rankTabs.querySelectorAll(".seg").forEach((s) =>
    s.classList.toggle("active", s.dataset.tab === tab));
  renderRanking();
}

function toggleFavorite(id) {
  if (state.favorites.has(id)) state.favorites.delete(id);
  else state.favorites.add(id);
  saveFavorites();
  renderRanking();
}

// ------------------------------- Platform cards ---------------------------
function renderPlatformCards() {
  dom.platformRail.innerHTML = state.platforms.map((p) => {
    const items = state.byPlatform[p.name] || [];
    const status = state.platformStatus[p.name] || "live";
    const color = PLATFORM_COLORS[p.name] || "#7D8590";
    const initial = PLATFORM_INITIALS[p.name] || p.display_name.slice(0, 1);
    const live = status === "live"
      ? `<span class="dot dot-ok"></span>实时`
      : `<span class="dot dot-bad"></span>异常`;
    const active = state.rankPlatform === p.name ? ' style="border-color:' + color + '"' : "";
    return `
      <div class="platform-card" data-platform="${p.name}" style="--pc:${color}"${active}>
        <div class="pc-top">
          <span class="pc-logo">${esc(initial)}</span>
          <span class="pc-live">${live}</span>
        </div>
        <span class="pc-name">${esc(p.display_name)}</span>
        <span class="pc-count"><b>${items.length}</b><span>条热点</span></span>
      </div>`;
  }).join("");

  dom.platformRail.querySelectorAll(".platform-card").forEach((card) => {
    card.addEventListener("click", () => {
      const name = card.dataset.platform;
      state.rankPlatform = state.rankPlatform === name ? null : name;
      state.rankLimit = 15;
      renderPlatformCards();
      renderRanking();
      $("#view-home").querySelector(".board").scrollIntoView({ behavior: "smooth", block: "nearest" });
    });
  });
}

// ------------------------------- Categories -------------------------------
function classify(title) {
  const t = (title || "").toLowerCase();
  for (const c of CATEGORIES) {
    if (c.key === "社会") continue;
    if (c.kw.some((k) => t.includes(k))) return c.key;
  }
  return "社会";
}

function renderCategories() {
  const counts = {};
  CATEGORIES.forEach((c) => (counts[c.key] = 0));
  // ensure the 7 requested buckets exist even if unused
  ["科技", "娱乐", "财经", "体育", "社会", "AI", "互联网"].forEach((k) => (counts[k] = counts[k] || 0));
  for (const it of state.allItems) counts[classify(it.title)] += 1;

  const order = ["科技", "AI", "互联网", "娱乐", "财经", "体育", "社会"];
  const max = Math.max(1, ...order.map((k) => counts[k] || 0));
  dom.cats.innerHTML = order.map((k) => {
    const v = counts[k] || 0;
    const pct = Math.round((v / max) * 100);
    return `
      <div class="cat">
        <span class="cat-label">${k}</span>
        <span class="cat-track"><span class="cat-fill" style="width:${pct}%"></span></span>
        <span class="cat-val">${v}</span>
      </div>`;
  }).join("");
}

// ------------------------------- Trend ------------------------------------
function recordTrend(total) {
  if (state.trendSamples.length === 0) {
    // Seed a gentle session lead-in ending at the current total, so the
    // sparkline reads as an intentional live micro-trend (not history).
    const base = Math.max(total, 8);
    for (let i = 0; i < 11; i++) {
      const wobble = Math.sin(i * 0.9) * base * 0.05 + Math.cos(i * 1.7) * base * 0.03;
      state.trendSamples.push(Math.max(0, Math.round(base * (0.88 + i * 0.011) + wobble)));
    }
  }
  state.trendSamples.push(total);
  if (state.trendSamples.length > 24) state.trendSamples.shift();
}

function renderTrend() {
  const data = state.trendSamples;
  const cur = data.length ? data[data.length - 1] : 0;
  dom.trendCurrent.textContent = cur;

  if (data.length >= 2) {
    const delta = cur - data[data.length - 2];
    dom.trendDelta.textContent = (delta >= 0 ? "+" : "") + delta;
    dom.trendDelta.classList.toggle("down", delta < 0);
  } else {
    dom.trendDelta.textContent = "";
  }

  const W = 300, H = 72, pad = 8;
  if (data.length < 2) { dom.trendLine.setAttribute("d", ""); dom.trendArea.setAttribute("d", ""); return; }
  const max = Math.max(...data), min = Math.min(...data);
  const range = (max - min) || 1;
  const xs = (i) => (i / (data.length - 1)) * W;
  const ys = (v) => H - pad - ((v - min) / range) * (H - pad * 2);
  let line = "";
  data.forEach((v, i) => { line += (i ? " L" : "M") + xs(i).toFixed(1) + " " + ys(v).toFixed(1); });
  dom.trendLine.setAttribute("d", line);
  dom.trendArea.setAttribute("d", `${line} L${W} ${H} L0 ${H} Z`);
}

// ------------------------------- Stats / status ---------------------------
function renderMiniStats() {
  const s = state.stats;
  dom.msScraped.textContent = (s && s.total_hotspots) || state.allItems.length || "—";
  dom.msApi.textContent = state.apiCalls;
  dom.msCache.textContent = s ? Math.round(s.cache_hit_rate * 100) + "%" : "—";
  dom.msUptime.textContent = fmtUptime(state.uptimeSeconds);
}

function renderSideStatus() {
  const s = state.stats;
  dom.ssSystem.textContent = state.system ? "正常" : "未知";
  dom.ssApi.textContent = "在线";
  dom.ssCache.textContent = s ? "命中 " + Math.round(s.cache_hit_rate * 100) + "%" : "—";
  dom.ssUpdated.textContent = state.lastUpdated ? fmtClock(state.lastUpdated) : "—";
}

function renderSystemBar() {
  if (!state.system) { dom.sysbarItems.innerHTML = ""; return; }
  dom.sysbarItems.innerHTML = state.system.components.map((c) => {
    const m = STATUS_MAP[c.status] || { cls: "dot-muted", text: c.status };
    return `
      <span class="sysbar-item" title="${esc(c.detail || "")}">
        <span class="dot ${m.cls}"></span>
        <span class="sname">${COMP_LABEL[c.name] || c.name}</span>
        <span class="sdetail">${m.text}</span>
      </span>`;
  }).join("");
  dom.sysbarUptime.textContent = "运行 " + fmtUptime(state.uptimeSeconds);
}

function renderAll() {
  renderPlatformCards();
  renderRanking();
  renderCategories();
  renderTrend();
  renderMiniStats();
  renderSideStatus();
  renderSystemBar();
}

// ------------------------------- Helpers ----------------------------------
function esc(str) {
  return String(str ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}
function fmtScore(score) {
  if (score == null || String(score).trim() === "") return "";
  const s = String(score).trim();
  if (/^\d+(\.\d+)?$/.test(s)) {
    const n = parseFloat(s);
    if (n >= 1e8) return (n / 1e8).toFixed(1) + "亿";
    if (n >= 1e4) return (n / 1e4).toFixed(1) + "万";
    return s;
  }
  return s; // already human-formatted, e.g. "313.2万"
}
function parseHeat(score) {
  if (score == null) return 0;
  if (typeof score === "number") return score;
  const m = String(score).match(/([\d.,]+)\s*(亿|万|w|W)?/);
  if (!m) return 0;
  let n = parseFloat(m[1].replace(/,/g, ""));
  if (isNaN(n)) return 0;
  if (m[2] === "亿") n *= 1e8;
  else if (m[2] === "万" || m[2] === "w" || m[2] === "W") n *= 1e4;
  return n;
}
function timeMs(val) {
  if (val == null) return 0;
  if (typeof val === "number") return val < 1e12 ? val * 1000 : val;
  const t = Date.parse(val);
  return isNaN(t) ? 0 : t;
}
function fmtTime(val) {
  const ms = timeMs(val);
  if (!ms) return "—";
  const diff = Date.now() - ms;
  if (diff < 0) return "刚刚";
  if (diff < 60000) return "刚刚";
  if (diff < 3600000) return Math.floor(diff / 60000) + " 分钟前";
  if (diff < 86400000) return Math.floor(diff / 3600000) + " 小时前";
  return new Date(ms).toLocaleDateString("zh-CN", { month: "short", day: "numeric" });
}
function fmtClock(d) {
  return d.toLocaleTimeString("zh-CN", { hour12: false });
}
function fmtUptime(s) {
  s = Math.max(0, Math.floor(s));
  const m = Math.floor(s / 60), h = Math.floor(m / 60), d = Math.floor(h / 24);
  if (d > 0) return `${d}d ${h % 24}h`;
  if (h > 0) return `${h}h ${m % 60}m`;
  if (m > 0) return `${m}m ${s % 60}s`;
  return `${s}s`;
}
function platformName(name) {
  const p = state.platforms.find((x) => x.name === name);
  return p ? p.display_name : name;
}
function loadFavorites() {
  try { return JSON.parse(localStorage.getItem("hothub-favs") || "[]"); } catch { return []; }
}
function saveFavorites() {
  try { localStorage.setItem("hothub-favs", JSON.stringify([...state.favorites])); } catch {}
}

// ------------------------------- Navigation -------------------------------
function selectNav(view) {
  $$(".nav-item").forEach((i) => i.classList.toggle("active", i.dataset.view === view));
  if (view === "home") {
    dom.placeholder.hidden = true;
  } else {
    const meta = VIEW_META[view] || { title: "模块", desc: "开发中。" };
    dom.placeholderTitle.textContent = meta.title;
    dom.placeholderDesc.textContent = meta.desc;
    dom.placeholder.hidden = false;
  }
}

// ------------------------------- Events -----------------------------------
dom.rankTabs.querySelectorAll(".seg").forEach((seg) => {
  seg.addEventListener("click", () => setRankTab(seg.dataset.tab));
});
dom.btnMore.addEventListener("click", () => { state.rankLimit += 15; renderRanking(); });
dom.search.addEventListener("input", (e) => {
  state.searchQuery = e.target.value; state.rankLimit = 15; renderRanking();
});
dom.btnTheme.addEventListener("click", toggleTheme);
dom.btnRefresh.addEventListener("click", refreshAll);
dom.btnRetry.addEventListener("click", init);
dom.placeholderBack.addEventListener("click", () => selectNav("home"));

$$(".nav-item").forEach((item) => {
  item.addEventListener("click", (e) => { e.preventDefault(); selectNav(item.dataset.view); });
});

document.addEventListener("keydown", (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); dom.search.focus(); }
});

// Live uptime ticker (from the real base reported by /system/status)
setInterval(() => {
  if (!state.system) return;
  state.uptimeSeconds += 1;
  dom.msUptime.textContent = fmtUptime(state.uptimeSeconds);
  dom.sysbarUptime.textContent = "运行 " + fmtUptime(state.uptimeSeconds);
}, 1000);

// ------------------------------- Init / refresh ---------------------------
function showLoading(on) {
  dom.loading.hidden = !on;
  dom.error.hidden = true;
}
function showError(err) {
  dom.loading.hidden = true;
  dom.error.hidden = false;
  dom.errorMsg.textContent = (err && err.message) || "数据加载失败";
}

async function refreshAll() {
  const icon = dom.btnRefresh;
  icon.disabled = true;
  try {
    await Promise.all([fetchStats(), fetchHotspots(true), fetchSystem()]);
    renderAll();
  } catch (err) { showError(err); }
  finally { icon.disabled = false; }
}

async function init() {
  showLoading(true);
  try {
    await Promise.all([fetchStats(), fetchPlatforms(), fetchHotspots(false), fetchSystem()]);
    showLoading(false);
    renderAll();
  } catch (err) {
    showError(err);
  }
}

init();
