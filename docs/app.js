"use strict";

/* ---------------- i18n ---------------- */
const I18N = {
  ko: {
    title: "공개 Oncology 오믹스 데이터 모니터",
    subtitle: "공간전사체 · 공간단백체 중심 · 라이선스/학습가능성 태깅 · 매주 자동 갱신",
    search_ph: "이름·설명·기관 검색…",
    train_only: "학습 가능만 (CC0/CC-BY)",
    spatial_only: "공간 데이터만",
    new_only: "이번 주 신규만",
    fav_only: "★ 즐겨찾기만",
    reset: "초기화",
    export: "CSV 내보내기",
    foot: "메타데이터만 수집 · 데이터는 각 소스에서 제공 · ",
    total: "전체 데이터셋", neww: "이번 주 신규", spatial: "공간 데이터",
    trainable: "학습 가능(CC0/CC-BY)", updated: "최종 갱신", sources: "소스별",
    results: "건 표시", of: " / 전체 ",
    c_fav: "★", c_new: "NEW", c_name: "데이터셋", c_source: "소스",
    c_modality: "모달리티", c_platform: "플랫폼", c_size: "크기",
    c_license: "라이선스/학습", c_organism: "생물종", c_org: "기관(만든곳)",
    c_date: "게시일",
    all: "전체", f_source: "소스", f_modality: "모달리티", f_platform: "플랫폼",
    f_cancer_type: "암종", f_train_usability: "학습가능성",
    f_access_level: "접근", f_organism: "생물종",
  },
  en: {
    title: "Public Oncology Omics Data Monitor",
    subtitle: "Spatial transcriptomics · spatial proteomics · license/trainability tagging · weekly auto-update",
    search_ph: "Search name, description, organization…",
    train_only: "Train-usable only (CC0/CC-BY)",
    spatial_only: "Spatial only",
    new_only: "New this week only",
    fav_only: "★ Favorites only",
    reset: "Reset",
    export: "Export CSV",
    foot: "Metadata only · data served by each source · ",
    total: "Total datasets", neww: "New this week", spatial: "Spatial datasets",
    trainable: "Train-usable (CC0/CC-BY)", updated: "Last updated", sources: "By source",
    results: " shown", of: " / of ",
    c_fav: "★", c_new: "NEW", c_name: "Dataset", c_source: "Source",
    c_modality: "Modality", c_platform: "Platform", c_size: "Size",
    c_license: "License/Train", c_organism: "Organism", c_org: "Organization",
    c_date: "Published",
    all: "All", f_source: "Source", f_modality: "Modality", f_platform: "Platform",
    f_cancer_type: "Cancer type", f_train_usability: "Trainability",
    f_access_level: "Access", f_organism: "Organism",
  },
};
let LANG = localStorage.getItem("odd_lang") || "ko";
const t = (k) => (I18N[LANG][k] ?? k);

/* ---------------- state ---------------- */
let DATA = [], META = {}, VIEW = [];
let page = 1, perPage = 50;
let sortKey = "published_date", sortDir = -1;
const FACETS = ["source", "modality", "platform", "cancer_type",
  "train_usability", "access_level", "organism"];
const LISTY = new Set(["modality", "cancer_type"]);
const favs = new Set(JSON.parse(localStorage.getItem("odd_favs") || "[]"));

const USABILITY_ORDER = { usable: 0, attribution: 1, non_commercial: 2, restricted: 3, unknown: 4 };

/* ---------------- load ---------------- */
Promise.all([
  fetch("catalog.json").then((r) => r.json()),
  fetch("meta.json").then((r) => r.json()).catch(() => ({})),
]).then(([cat, meta]) => {
  DATA = cat; META = meta;
  buildFacets();
  bindEvents();
  applyI18n();
  render();
});

/* ---------------- facets ---------------- */
function uniqueValues(key) {
  const c = new Map();
  for (const r of DATA) {
    const v = r[key];
    const vals = Array.isArray(v) ? v : [v];
    for (const x of vals) {
      if (x === null || x === undefined || x === "") continue;
      c.set(x, (c.get(x) || 0) + 1);
    }
  }
  return [...c.entries()].sort((a, b) => b[1] - a[1]);
}

function buildFacets() {
  const wrap = document.getElementById("facets");
  wrap.innerHTML = "";
  for (const key of FACETS) {
    const sel = document.createElement("select");
    sel.id = "f_" + key;
    sel.dataset.key = key;
    const opt0 = document.createElement("option");
    opt0.value = "";
    opt0.textContent = `${t("f_" + key)}: ${t("all")}`;
    opt0.dataset.i18nLabel = key;
    sel.appendChild(opt0);
    for (const [val, cnt] of uniqueValues(key)) {
      const o = document.createElement("option");
      o.value = val;
      o.textContent = `${val} (${cnt})`;
      sel.appendChild(o);
    }
    sel.addEventListener("change", () => { page = 1; render(); });
    wrap.appendChild(sel);
  }
}

/* ---------------- filtering ---------------- */
function currentFilters() {
  const f = {};
  for (const key of FACETS) {
    const v = document.getElementById("f_" + key).value;
    if (v) f[key] = v;
  }
  return f;
}

function matchesText(r, q) {
  if (!q) return true;
  const blob = [r.name, r.description, r.organization, r.owner,
    (r.modality || []).join(" "), (r.cancer_type || []).join(" "), r.platform]
    .filter(Boolean).join(" ").toLowerCase();
  return q.toLowerCase().split(/\s+/).every((w) => blob.includes(w));
}

function computeView() {
  const q = document.getElementById("search").value.trim();
  const f = currentFilters();
  const trainOnly = document.getElementById("trainOnly").checked;
  const spatialOnly = document.getElementById("spatialOnly").checked;
  const newOnly = document.getElementById("newOnly").checked;
  const favOnly = document.getElementById("favOnly").checked;

  VIEW = DATA.filter((r) => {
    if (!matchesText(r, q)) return false;
    for (const [key, val] of Object.entries(f)) {
      if (LISTY.has(key)) {
        if (!(r[key] || []).includes(val)) return false;
      } else if (String(r[key] ?? "") !== val) return false;
    }
    if (trainOnly && !["usable", "attribution"].includes(r.train_usability)) return false;
    if (spatialOnly && !r.is_spatial) return false;
    if (newOnly && !r.new_this_week) return false;
    if (favOnly && !favs.has(r.id)) return false;
    return true;
  });

  VIEW.sort((a, b) => {
    let x, y;
    if (sortKey === "train_usability") {
      x = USABILITY_ORDER[a.train_usability] ?? 9;
      y = USABILITY_ORDER[b.train_usability] ?? 9;
    } else {
      x = a[sortKey]; y = b[sortKey];
      if (Array.isArray(x)) x = x.join(",");
      if (Array.isArray(y)) y = y.join(",");
      x = (x ?? "").toString().toLowerCase();
      y = (y ?? "").toString().toLowerCase();
    }
    if (x < y) return -1 * sortDir;
    if (x > y) return 1 * sortDir;
    return 0;
  });
}

/* ---------------- render ---------------- */
const COLS = [
  { key: "fav", label: "c_fav", sortable: false },
  { key: "new_this_week", label: "c_new", sortable: true },
  { key: "name", label: "c_name", sortable: true },
  { key: "source", label: "c_source", sortable: true },
  { key: "modality", label: "c_modality", sortable: true },
  { key: "platform", label: "c_platform", sortable: true },
  { key: "size", label: "c_size", sortable: true },
  { key: "train_usability", label: "c_license", sortable: true },
  { key: "organism", label: "c_organism", sortable: true },
  { key: "organization", label: "c_org", sortable: true },
  { key: "published_date", label: "c_date", sortable: true },
];

function renderStats() {
  const nTrain = DATA.filter((r) => ["usable", "attribution"].includes(r.train_usability)).length;
  const nSpatial = DATA.filter((r) => r.is_spatial).length;
  const el = document.getElementById("stats");
  el.innerHTML = `
    <div class="stat"><div class="num">${DATA.length}</div><div class="lbl">${t("total")}</div></div>
    <div class="stat"><div class="num red">${META.new_this_week ?? 0}</div><div class="lbl">${t("neww")}</div></div>
    <div class="stat"><div class="num">${nSpatial}</div><div class="lbl">${t("spatial")}</div></div>
    <div class="stat"><div class="num">${nTrain}</div><div class="lbl">${t("trainable")}</div></div>
    <div class="stat srcs"><div class="lbl">${t("sources")}</div>
      ${Object.entries(META.source_totals || {}).map(([s, n]) =>
        `<span class="srcline">${s}: ${n}</span>`).join("")}
    </div>
    <div class="stat"><div class="num" style="font-size:15px">${META.last_run || "-"}</div><div class="lbl">${t("updated")}</div></div>`;
}

function renderHead() {
  const tr = document.getElementById("headrow");
  tr.innerHTML = "";
  for (const c of COLS) {
    const th = document.createElement("th");
    const arrow = (c.key === sortKey) ? ` <span class="arrow">${sortDir === 1 ? "▲" : "▼"}</span>` : "";
    th.innerHTML = t(c.label) + arrow;
    if (c.sortable) th.addEventListener("click", () => {
      if (sortKey === c.key) sortDir *= -1;
      else { sortKey = c.key; sortDir = c.key === "published_date" ? -1 : 1; }
      render();
    });
    tr.appendChild(th);
  }
}

function tags(list, spatialSet) {
  return (list || []).map((x) =>
    `<span class="tag${spatialSet && spatialSet.has(x) ? " spatial" : ""}">${x}</span>`).join("");
}
const SPATIAL_MODS = new Set(["spatial_transcriptomics", "spatial_proteomics"]);

function esc(s) {
  return (s ?? "").toString().replace(/[&<>"]/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

function renderRows() {
  const start = (page - 1) * perPage;
  const slice = VIEW.slice(start, start + perPage);
  const tb = document.getElementById("rows");
  tb.innerHTML = "";
  for (const r of slice) {
    const tr = document.createElement("tr");
    const lic = r.license_class && r.license_class !== "unknown"
      ? `<span class="tag">${r.license_class}</span>` : "";
    tr.innerHTML = `
      <td><span class="star ${favs.has(r.id) ? "on" : ""}" data-id="${esc(r.id)}">★</span></td>
      <td>${r.new_this_week ? `<span class="new-badge">NEW</span>` : ""}</td>
      <td class="name">
        <a href="${esc(r.url)}" target="_blank" rel="noopener">${esc(r.name)}</a>
        <div class="desc">${esc((r.description || "").slice(0, 140))}</div>
      </td>
      <td><span class="src-pill">${esc(r.source)}</span></td>
      <td>${tags(r.modality, SPATIAL_MODS)}</td>
      <td>${esc(r.platform || "")}</td>
      <td>${esc(r.size || "")}</td>
      <td><span class="badge b-${r.train_usability}">${r.train_usability}</span> ${lic}</td>
      <td>${esc(r.organism || "")}</td>
      <td>${esc(r.organization || "")}</td>
      <td>${esc(r.published_date || "")}</td>`;
    tb.appendChild(tr);
  }
  tb.querySelectorAll(".star").forEach((s) =>
    s.addEventListener("click", () => toggleFav(s.dataset.id)));
}

function renderPager() {
  const pages = Math.max(1, Math.ceil(VIEW.length / perPage));
  if (page > pages) page = pages;
  const nav = document.getElementById("pager");
  nav.innerHTML = "";
  const mk = (label, p, opts = {}) => {
    const b = document.createElement("button");
    b.textContent = label;
    if (opts.active) b.classList.add("active");
    if (opts.disabled) b.disabled = true;
    else b.addEventListener("click", () => { page = p; render(); window.scrollTo(0, 0); });
    nav.appendChild(b);
  };
  mk("‹", page - 1, { disabled: page <= 1 });
  const win = 2;
  for (let p = 1; p <= pages; p++) {
    if (p === 1 || p === pages || Math.abs(p - page) <= win) {
      mk(String(p), p, { active: p === page });
    } else if (Math.abs(p - page) === win + 1) {
      const span = document.createElement("span"); span.textContent = "…"; nav.appendChild(span);
    }
  }
  mk("›", page + 1, { disabled: page >= pages });
}

function render() {
  computeView();
  renderStats();
  renderHead();
  renderRows();
  renderPager();
  document.getElementById("resultCount").textContent =
    `${VIEW.length}${t("results")}${t("of")}${DATA.length}`;
}

/* ---------------- favorites ---------------- */
function toggleFav(id) {
  if (favs.has(id)) favs.delete(id); else favs.add(id);
  localStorage.setItem("odd_favs", JSON.stringify([...favs]));
  render();
}

/* ---------------- CSV export ---------------- */
function exportCsv() {
  const cols = ["id", "name", "source", "url", "modality", "platform", "size",
    "organism", "cancer_type", "license_class", "train_usability",
    "access_level", "organization", "owner", "published_date", "new_this_week"];
  const esc = (v) => {
    if (Array.isArray(v)) v = v.join("; ");
    v = (v ?? "").toString().replace(/"/g, '""');
    return `"${v}"`;
  };
  const lines = [cols.join(",")];
  for (const r of VIEW) lines.push(cols.map((c) => esc(r[c])).join(","));
  const blob = new Blob(["﻿" + lines.join("\n")], { type: "text/csv;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `omics_catalog_${(META.last_run || "export")}.csv`;
  a.click();
}

/* ---------------- events + i18n ---------------- */
function bindEvents() {
  let d;
  document.getElementById("search").addEventListener("input", () => {
    clearTimeout(d); d = setTimeout(() => { page = 1; render(); }, 200);
  });
  for (const id of ["trainOnly", "spatialOnly", "newOnly", "favOnly"]) {
    document.getElementById(id).addEventListener("change", () => { page = 1; render(); });
  }
  document.getElementById("reset").addEventListener("click", () => {
    document.getElementById("search").value = "";
    FACETS.forEach((k) => (document.getElementById("f_" + k).value = ""));
    ["trainOnly", "spatialOnly", "newOnly", "favOnly"].forEach((id) =>
      (document.getElementById(id).checked = false));
    page = 1; render();
  });
  document.getElementById("exportCsv").addEventListener("click", exportCsv);
  document.getElementById("langToggle").addEventListener("click", () => {
    LANG = LANG === "ko" ? "en" : "ko";
    localStorage.setItem("odd_lang", LANG);
    document.getElementById("langToggle").textContent = LANG === "ko" ? "EN" : "KO";
    document.documentElement.lang = LANG;
    applyI18n(); buildFacets(); render();
  });
}

function applyI18n() {
  document.getElementById("langToggle").textContent = LANG === "ko" ? "EN" : "KO";
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-ph]").forEach((el) => {
    el.placeholder = t(el.dataset.i18nPh);
  });
}
