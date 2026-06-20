const state = {
  platform: "all",
  platforms: [],
};

const tabsEl = document.getElementById("tabs");
const contentEl = document.getElementById("content");
const updatedAtEl = document.getElementById("updated-at");
const limitEl = document.getElementById("limit");
const refreshBtn = document.getElementById("refresh");

async function loadPlatforms() {
  const res = await fetch("/platforms");
  if (!res.ok) throw new Error("无法获取平台列表");
  state.platforms = await res.json();
  renderTabs();
}

function renderTabs() {
  const items = [{ name: "all", display_name: "全部" }, ...state.platforms];
  tabsEl.innerHTML = items
    .map(
      (p) =>
        `<button type="button" class="tab${state.platform === p.name ? " active" : ""}" data-platform="${p.name}">${escapeHtml(p.display_name)}</button>`
    )
    .join("");

  tabsEl.querySelectorAll(".tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.platform = btn.dataset.platform;
      renderTabs();
      loadHotspots(false);
    });
  });
}

async function loadHotspots(refresh = false) {
  contentEl.className = "content loading";
  contentEl.textContent = "正在加载数据…";

  const limit = limitEl.value;
  const query = `limit=${limit}${refresh ? "&refresh=true" : ""}`;
  const url =
    state.platform === "all"
      ? `/hotspots?${query}`
      : `/hotspots/${state.platform}?${query}`;

  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error(await res.text());
    renderHotspots(await res.json());
  } catch (err) {
    contentEl.className = "content error";
    contentEl.textContent = `加载失败：${err.message}`;
  }
}

function renderHotspots(data) {
  updatedAtEl.textContent = `更新于 ${formatTime(data.fetched_at)}`;

  if (!data.platforms.length) {
    contentEl.className = "content empty";
    contentEl.textContent = "暂无数据";
    return;
  }

  contentEl.className = "grid";
  contentEl.innerHTML = data.platforms.map(renderPlatformCard).join("");
}

function renderPlatformCard(platform) {
  const isError = platform.source_status === "error";
  const items = platform.items
    .map(
      (item) => `
      <li class="item">
        <span class="rank${(item.rank || 0) <= 3 ? " top" : ""}">${item.rank || "-"}</span>
        <div class="item-body">
          <a href="${item.url || "#"}" target="_blank" rel="noopener">${escapeHtml(item.title)}</a>
          ${item.summary ? `<div class="summary">${escapeHtml(item.summary)}</div>` : ""}
        </div>
        ${item.score != null && item.score !== "" ? `<span class="score">${formatScore(item.score)}</span>` : ""}
      </li>`
    )
    .join("");

  return `
    <article class="card">
      <div class="card-head">
        <span>${escapeHtml(platform.display_name)}</span>
        <span class="badge${isError ? " warn" : ""}">${isError ? "降级" : "实时"}</span>
      </div>
      <ol class="list">${items}</ol>
    </article>`;
}

function formatTime(iso) {
  return new Date(iso).toLocaleString("zh-CN");
}

function formatScore(score) {
  if (typeof score === "number" && score >= 10000) {
    return `${(score / 10000).toFixed(1)}万`;
  }
  return String(score);
}

function escapeHtml(text) {
  return String(text).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]
  );
}

refreshBtn.addEventListener("click", () => loadHotspots(true));
limitEl.addEventListener("change", () => loadHotspots(false));

loadPlatforms()
  .then(() => loadHotspots(false))
  .catch((err) => {
    contentEl.className = "content error";
    contentEl.textContent = `初始化失败：${err.message}`;
  });
