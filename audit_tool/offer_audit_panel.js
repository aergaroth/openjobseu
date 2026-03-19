const ids = [
  "q",
  "status",
  "source",
  "company",
  "title",
  "remote_scope",
  "remote_class",
  "geo_class",
  "compliance_status",
  "min_compliance_score",
  "max_compliance_score",
  "limit",
  "offset"
];

const registrySelectIds = [
  "status",
  "source",
  "remote_class",
  "geo_class",
  "compliance_status"
];

const JOB_COLS_DEF = [
  { key: "job_id", label: "ID", render: (j) => `<td class="mono">${esc(j.job_id)}</td>` },
  { key: "source", label: "Source", render: (j) => `<td>${esc(j.source)}</td>` },
  { key: "title", label: "Title", render: (j) => `<td>${esc(j.title)}</td>` },
  { key: "company_name", label: "Company", render: (j) => `<td>${esc(j.company_name)}</td>` },
  { key: "source_department", label: "Source Dept", render: (j) => `<td>${esc(j.source_department)}</td>` },
  { key: "status", label: "Status", render: (j) => `<td>${esc(j.status)}</td>` },
  { key: "remote_class", label: "Remote class", render: (j) => `<td>${esc(j.remote_class)}</td>` },
  { key: "geo_class", label: "Geo class", render: (j) => `<td>${esc(j.geo_class)}</td>` },
  { key: "compliance_status", label: "Compliance", render: (j) => `<td>${esc(j.compliance_status)}</td>` },
  { key: "compliance_score", label: "Score", render: (j) => `<td>${esc(j.compliance_score)}</td>` },
  { key: "first_seen_at", label: "First seen", render: (j) => `<td class="mono">${esc(j.first_seen_at)}</td>` },
  { key: "last_seen_at", label: "Last seen", render: (j) => `<td class="mono">${esc(j.last_seen_at)}</td>` },
  { key: "url", label: "URL", render: (j) => {
    const u = esc(j.source_url || "");
    return `<td>${u ? `<a href="${u}" target="_blank" rel="noreferrer" onclick="event.stopPropagation()">open</a>` : ""}</td>`;
  }}
];
let jobColsActive = JSON.parse(localStorage.getItem('jobColsActive')) || JOB_COLS_DEF.map(c => c.key);
let currentJobs = [];

const COMP_COLS_DEF = [
  { key: "company_id", label: "ID", render: (c) => `<td class="mono" style="font-size: 0.75rem;">${esc(c.company_id).split('-')[0]}...</td>` },
  { key: "legal_name", label: "Legal Name", render: (c) => `<td><strong>${esc(c.legal_name)}</strong><br/><span style="color:var(--muted); font-size:0.75rem;">${esc(c.brand_name)}</span></td>` },
  { key: "hq_country", label: "HQ", render: (c) => `<td>${esc(c.hq_country)}</td>` },
  { key: "remote_posture", label: "Posture", render: (c) => `<td>${esc(c.remote_posture)}</td>` },
  { key: "eu_entity_verified", label: "EU", render: (c) => `<td>${c.eu_entity_verified ? 'Yes' : 'No'}</td>` },
  { key: "ats_provider", label: "ATS", render: (c) => `<td>${esc(c.ats_provider)}<br/><span class="mono" style="color:var(--muted); font-size:0.75rem;">${esc(c.ats_slug)}</span></td>` },
  { key: "signal_score", label: "Score", render: (c) => `<td><strong>${esc(c.signal_score)}</strong></td>` },
  { key: "total_jobs_count", label: "Jobs", render: (c) => `<td>${esc(c.total_jobs_count)}</td>` },
  { key: "approved_jobs_count", label: "Approv.", render: (c) => `<td>${esc(c.approved_jobs_count)}</td>` },
  { key: "last_active_job_at", label: "Last Active", render: (c) => `<td class="mono">${c.last_active_job_at ? esc(c.last_active_job_at).substring(0, 10) : ''}</td>` },
  { key: "is_active", label: "Active", render: (c) => `<td>${c.is_active ? 'Yes' : 'No'}</td>` }
];
let compColsActive = JSON.parse(localStorage.getItem('compColsActive')) || COMP_COLS_DEF.map(c => c.key);
let currentCompanies = [];

let debounceTimer = null;

function esc(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function paramsFromFilters() {
  const params = new URLSearchParams();
  for (const id of ids) {
    const el = document.getElementById(id);
    if (!el) continue;
    const value = (el.value || "").trim();
    if (value !== "") params.set(id, value);
  }
  return params;
}

function renderCountMap(nodeId, counts, maxItems = 12) {
  const node = document.getElementById(nodeId);
  if (!node) return;
  const entries = Object.entries(counts || {});
  if (entries.length === 0) {
    node.innerHTML = '<span class="chip">none</span>';
    return;
  }
  
  let html = entries.slice(0, maxItems)
    .map(([key, value]) => `<span class="chip">${esc(key)}: ${esc(value)}</span>`)
    .join("");
    
  if (entries.length > maxItems) {
    html += `<span class="chip" style="background: transparent; border: 1px dashed var(--muted); color: var(--muted);">+${entries.length - maxItems} more</span>`;
  }
  node.innerHTML = html;
}

function renderJobColsMenu() {
  const menu = document.getElementById('job-cols-menu');
  if(!menu) return;
  menu.innerHTML = JOB_COLS_DEF.map(c => `<label><input type="checkbox" value="${c.key}" ${jobColsActive.includes(c.key) ? 'checked' : ''} onchange="toggleJobCol(this)" /> ${c.label}</label>`).join('');
}
function toggleJobCol(cb) {
  if (cb.checked) jobColsActive.push(cb.value);
  else jobColsActive = jobColsActive.filter(k => k !== cb.value);
  jobColsActive = JOB_COLS_DEF.map(c => c.key).filter(k => jobColsActive.includes(k));
  localStorage.setItem('jobColsActive', JSON.stringify(jobColsActive));
  renderJobHeaders(); renderJobRows(currentJobs); updateTopScrollbar();
}
function renderJobHeaders() {
  const head = document.getElementById("jobs-head");
  if(head) head.innerHTML = JOB_COLS_DEF.filter(c => jobColsActive.includes(c.key)).map(c => `<th>${c.label}</th>`).join("");
}

function renderCompColsMenu() {
  const menu = document.getElementById('comp-cols-menu');
  if(!menu) return;
  menu.innerHTML = COMP_COLS_DEF.map(c => `<label><input type="checkbox" value="${c.key}" ${compColsActive.includes(c.key) ? 'checked' : ''} onchange="toggleCompCol(this)" /> ${c.label}</label>`).join('');
}
function toggleCompCol(cb) {
  if (cb.checked) compColsActive.push(cb.value);
  else compColsActive = compColsActive.filter(k => k !== cb.value);
  compColsActive = COMP_COLS_DEF.map(c => c.key).filter(k => compColsActive.includes(k));
  localStorage.setItem('compColsActive', JSON.stringify(compColsActive));
  renderCompHeaders(); renderCompRows(currentCompanies); updateTopScrollbar();
}
function renderCompHeaders() {
  const head = document.getElementById("comp-head");
  if(head) head.innerHTML = COMP_COLS_DEF.filter(c => compColsActive.includes(c.key)).map(c => `<th>${c.label}</th>`).join("");
}

document.addEventListener('click', (e) => {
  if (!e.target.closest('.column-toggler')) document.querySelectorAll('.column-toggler-menu').forEach(m => m.classList.remove('open'));
});

function toggleExpandRow(row) {
  const isSelected = row.classList.contains('selected');
  
  document.querySelectorAll('.job-row.selected').forEach(el => el.classList.remove('selected'));
  document.querySelectorAll('.details-row.open').forEach(el => el.classList.remove('open'));
  
  if (!isSelected) {
    row.classList.add('selected');
    if (row.nextElementSibling) row.nextElementSibling.classList.add('open');
  }
}

function renderJobRows(items) {
  const body = document.getElementById("rows");
  if (!body) return;
  if (!items || items.length === 0) {
    body.innerHTML = `<tr><td colspan="${jobColsActive.length}">No jobs found for current filter.</td></tr>`;
    return;
  }
  body.innerHTML = items.map((job) => {
    const jobJson = esc(JSON.stringify(job, null, 2));
    const cells = JOB_COLS_DEF.filter(c => jobColsActive.includes(c.key)).map(c => c.render(job)).join("");
    return `
      <tr class="job-row" onclick="toggleExpandRow(this)" title="Click to view raw JSON">
        ${cells}
      </tr>
      <tr class="details-row">
        <td colspan="${jobColsActive.length}">
          <pre class="json-dump">${jobJson}</pre>
        </td>
      </tr>
    `;
  }).join("");
}

function renderCompRows(items) {
  const body = document.getElementById("comp-rows");
  if (!body) return;
  if (!items || items.length === 0) {
    body.innerHTML = `<tr><td colspan="${compColsActive.length}">No companies match current filter.</td></tr>`;
    return;
  }
  body.innerHTML = items.map((comp) => {
    const compJson = esc(JSON.stringify(comp, null, 2));
    const cells = COMP_COLS_DEF.filter(c => compColsActive.includes(c.key)).map(c => c.render(comp)).join("");
    return `
      <tr class="job-row" onclick="toggleExpandRow(this)" title="Click to view raw JSON">
        ${cells}
      </tr>
      <tr class="details-row">
        <td colspan="${compColsActive.length}">
          <pre class="json-dump">${compJson}</pre>
        </td>
      </tr>
    `;
  }).join("");
}

let currentCompanyStats = [];
let currentSourceStats = [];

function renderCompanyStatsRowsFromCache() {
  const showZero = document.getElementById("show-zero-approved-chk")?.checked;
  const items = currentCompanyStats.filter(item => showZero || item.approved > 0);
  renderCompanyStatsRows(items);
}

function renderSourceStatsRowsFromCache() {
  const showZero = document.getElementById("show-zero-source-approved-chk")?.checked;
  const items = currentSourceStats.filter(item => showZero || item.approved > 0);
  renderSourceStatsRows(items);
}

function formatRatio(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "N/A";
  }
  return `${Number(value).toFixed(2)}%`;
}

function renderCompanyStatsRows(items) {
  const body = document.getElementById("company-stats-rows");
  if (!body) return;
  if (!items || items.length === 0) {
    body.innerHTML = '<tr><td colspan="5">No companies match threshold.</td></tr>';
    return;
  }

  body.innerHTML = items.map((row) => `
    <tr>
      <td>${esc(row.legal_name)}</td>
      <td>${esc(row.total_jobs)}</td>
      <td>${esc(row.approved)}</td>
      <td>${esc(row.rejected)}</td>
      <td>${esc(formatRatio(row.approved_ratio_pct))}</td>
    </tr>
  `).join("");
}

function renderSourceStatsRows(items) {
  const body = document.getElementById("source-stats-rows");
  if (!body) return;
  if (!items || items.length === 0) {
    body.innerHTML = '<tr><td colspan="5">No source stats in the last 7 days.</td></tr>';
    return;
  }

  body.innerHTML = items.map((row) => `
    <tr>
      <td>${esc(row.source ?? "null")}</td>
      <td>${esc(row.total_jobs)}</td>
      <td>${esc(row.approved)}</td>
      <td>${esc(row.rejected)}</td>
      <td>${esc(formatRatio(row.approved_ratio_pct))}</td>
    </tr>
  `).join("");
}

function populateSelectOptions(selectId, values) {
  const node = document.getElementById(selectId);
  if (!node) return;
  const currentValue = node.value || "";
  node.innerHTML = '<option value="">All</option>';
  for (const value of (values || [])) {
    const opt = document.createElement("option");
    opt.value = String(value);
    opt.textContent = String(value);
    node.appendChild(opt);
  }
  node.value = currentValue;
  if (node.value !== currentValue) {
    node.value = "";
  }
}

async function loadFilterRegistry() {
  const response = await fetch("/internal/audit/filters");
  if (!response.ok) {
    throw new Error(`audit filter registry request failed with status ${response.status}`);
  }
  const registry = await response.json();
  for (const id of registrySelectIds) {
    populateSelectOptions(id, registry?.[id] || []);
  }
}

async function loadJobs() {
  const params = paramsFromFilters();
  const response = await fetch(`/internal/audit/jobs?${params.toString()}`);
  if (!response.ok) {
    throw new Error(`audit request failed with status ${response.status}`);
  }
  const data = await response.json();
  document.getElementById("total-count").textContent = String(data.total || 0);
  renderCountMap("count-status", data.counts?.status || {});
  renderCountMap("count-source", data.counts?.source || {});
  renderCountMap("count-compliance", data.counts?.compliance_status || {});
  currentJobs = data.items || [];
  renderJobHeaders();
  renderJobRows(currentJobs);
  updateTopScrollbar();

  // Update pagination state
  const offsetEl = document.getElementById("offset");
  const limitEl = document.getElementById("limit");
  const offset = parseInt(offsetEl.value || "0", 10);
  const limit = parseInt(limitEl.value || "50", 10);
  const total = data.total || 0;

  const pageInfo = document.getElementById("page-info");
  if (pageInfo) {
    const end = total === 0 ? 0 : Math.min(offset + limit, total);
    pageInfo.textContent = total === 0 ? "0 - 0 of 0" : `${offset + 1} - ${end} of ${total}`;
  }

  document.getElementById("prev-btn").disabled = offset <= 0;
  document.getElementById("next-btn").disabled = (offset + limit) >= total;
}

async function loadCompanies() {
  const params = new URLSearchParams();
  for (const id of ["comp_q", "comp_ats", "comp_active", "comp_min_score", "comp_limit", "comp_offset"]) {
    const el = document.getElementById(id);
    if (!el) continue;
    const val = (el.value || "").trim();
    if (val !== "") params.set(id.replace("comp_", ""), val);
  }
  
  const res = await fetch(`/internal/audit/companies?${params.toString()}`);
  if (!res.ok) throw new Error(`Companies request failed: ${res.status}`);
  const data = await res.json();
  
  currentCompanies = data.items || [];
  document.getElementById("comp-total-count").textContent = String(data.total || 0);
  
  const offset = parseInt(document.getElementById("comp_offset").value || "0", 10);
  const limit = parseInt(document.getElementById("comp_limit").value || "50", 10);
  const total = data.total || 0;
  
  const pageInfo = document.getElementById("comp-page-info");
  if (pageInfo) {
    const end = total === 0 ? 0 : Math.min(offset + limit, total);
    pageInfo.textContent = total === 0 ? "0 - 0 of 0" : `${offset + 1} - ${end} of ${total}`;
  }

  document.getElementById("comp-prev-btn").disabled = offset <= 0;
  document.getElementById("comp-next-btn").disabled = (offset + limit) >= total;

  renderCompHeaders();
  renderCompRows(currentCompanies);
  updateTopScrollbar();
}

async function safeLoadCompanies() {
  try {
    await loadCompanies();
  } catch (error) {
    const body = document.getElementById("comp-rows");
    if(body) body.innerHTML = `<tr><td class="error" colspan="${compColsActive.length}">${esc(error.message)}</td></tr>`;
    updateTopScrollbar();
  }
}

async function safeLoadJobs() {
  try {
    await loadJobs();
  } catch (error) {
    const body = document.getElementById("rows");
    body.innerHTML = `<tr><td class="error" colspan="13">${esc(error.message)}</td></tr>`;
    updateTopScrollbar();
  }
}

async function loadAuditStats() {
  const [companyResponse, sourceResponse] = await Promise.all([
    fetch("/internal/audit/stats/company"),
    fetch("/internal/audit/stats/source-7d"),
  ]);

  if (!companyResponse.ok) {
    throw new Error(`company stats request failed with status ${companyResponse.status}`);
  }
  if (!sourceResponse.ok) {
    throw new Error(`source stats request failed with status ${sourceResponse.status}`);
  }

  const companyPayload = await companyResponse.json();
  const sourcePayload = await sourceResponse.json();

  currentCompanyStats = companyPayload.items || [];
  renderCompanyStatsRowsFromCache();
  currentSourceStats = sourcePayload.items || [];
  renderSourceStatsRowsFromCache();

  const companyMeta = document.getElementById("company-stats-meta");
  const sourceMeta = document.getElementById("source-stats-meta");
  if (companyMeta) {
    companyMeta.textContent =
      `${(companyPayload.items || []).length} companies · threshold: total jobs > ${companyPayload.min_total_jobs}`;
  }
  if (sourceMeta) {
    sourceMeta.textContent =
      `${(sourcePayload.items || []).length} sources · window: ${sourcePayload.window}`;
  }
}

async function safeLoadAuditStats() {
  try {
    await loadAuditStats();
  } catch (error) {
    const companyBody = document.getElementById("company-stats-rows");
    const sourceBody = document.getElementById("source-stats-rows");
    const msg = esc(error.message);
    if (companyBody) {
      companyBody.innerHTML = `<tr><td class="error" colspan="5">${msg}</td></tr>`;
    }
    if (sourceBody) {
      sourceBody.innerHTML = `<tr><td class="error" colspan="5">${msg}</td></tr>`;
    }
  }
}

async function loadAtsHealth() {
  const response = await fetch("/internal/audit/ats-health?days_threshold=3");
  if (!response.ok) throw new Error(`ats-health request failed`);
  const payload = await response.json();
  const body = document.getElementById("ats-health-rows");
  const items = payload.items || [];
  if (items.length === 0) {
    body.innerHTML = '<tr><td colspan="7">All integrations look healthy!</td></tr>';
  } else {
    body.innerHTML = items.map(row => `
      <tr>
        <td>${esc(row.legal_name)}</td>
        <td>${esc(row.provider)}</td>
        <td class="mono">${esc(row.ats_slug)}</td>
        <td class="mono">${row.last_sync_at ? esc(row.last_sync_at) : 'Never'}</td>
        <td class="mono">${esc(row.created_at)}</td>
        <td>${row.careers_url ? `<a href="${esc(row.careers_url)}" target="_blank" rel="noreferrer">open</a>` : "N/A"}</td>
        <td>
          <button type="button" style="min-width:auto; padding: 4px 8px; font-size:0.75rem; margin-right: 4px;" onclick="runForceSync(this, '${esc(row.company_ats_id)}')">Force Sync</button>
          <button type="button" class="btn-danger" style="min-width:auto; padding: 4px 8px; font-size:0.75rem;" onclick="deactivateAts('${esc(row.company_ats_id)}')">Deactivate</button>
        </td>
      </tr>
    `).join("");
  }
  document.getElementById("ats-health-meta").textContent = `${items.length} stale integrations found.`;
}

async function safeLoadAtsHealth() {
  try { await loadAtsHealth(); } catch (e) {
    const body = document.getElementById("ats-health-rows");
    if (body) body.innerHTML = `<tr><td class="error" colspan="7">${esc(e.message)}</td></tr>`;
  }
}

function updateDiff(id, value) {
  const el = document.getElementById(id);
  if (!el) return;
  const num = parseInt(value, 10) || 0;
  el.textContent = `+${num} (24h)`;
  if (num > 0) el.classList.remove("zero");
  else el.classList.add("zero");
}

async function loadMetrics() {
  const response = await fetch("/internal/metrics");
  if (!response.ok) {
    throw new Error(`metrics request failed with status ${response.status}`);
  }
  const data = await response.json();
  
  document.getElementById("metric-jobs-total").textContent = data.jobs_total ?? "0";
  updateDiff("metric-jobs-24h", data.jobs_24h);
  document.getElementById("metric-companies-total").textContent = data.companies_total ?? "0";
  updateDiff("metric-companies-24h", data.companies_24h);
  document.getElementById("metric-company-ats-total").textContent = data.company_ats_total ?? "0";
  updateDiff("metric-company-ats-24h", data.company_ats_24h);
  
  const lastTick = data.last_tick_at ? new Date(data.last_tick_at).toLocaleString() : "N/A";
  document.getElementById("metric-last-tick-at").textContent = lastTick;
}

async function safeLoadMetrics() {
  try { await loadMetrics(); } catch (error) { document.getElementById("metric-last-tick-at").textContent = "Error"; }
}

async function safeLoadAll() {
  await Promise.all([safeLoadJobs(), safeLoadCompanies(), safeLoadAuditStats(), safeLoadMetrics(), safeLoadAtsHealth()]);
}
let compDebounceTimer = null;
function scheduleCompLoad() {
  if (compDebounceTimer) clearTimeout(compDebounceTimer);
  compDebounceTimer = setTimeout(safeLoadCompanies, 250);
}
for (const id of ["comp_q", "comp_ats", "comp_active", "comp_min_score", "comp_limit", "comp_offset"]) {
  const el = document.getElementById(id);
  if (el) {
    el.addEventListener("input", scheduleCompLoad);
    el.addEventListener("change", scheduleCompLoad);
  }
}

document.getElementById("comp-prev-btn").addEventListener("click", () => {
  const el = document.getElementById("comp_offset");
  const limit = parseInt(document.getElementById("comp_limit").value || "50", 10);
  el.value = Math.max(0, parseInt(el.value || "0", 10) - limit);
  safeLoadCompanies();
});

document.getElementById("comp-next-btn").addEventListener("click", () => {
  const el = document.getElementById("comp_offset");
  const limit = parseInt(document.getElementById("comp_limit").value || "50", 10);
  el.value = parseInt(el.value || "0", 10) + limit;
  safeLoadCompanies();
});

async function runTickDev() {
  const button = document.getElementById("tick-btn");
  const meta = document.getElementById("tick-meta");
  const out = document.getElementById("tick-output");
  const statusContainer = document.getElementById("task-status-container");
  button.disabled = true;
  button.classList.add("loading");
  meta.textContent = "running...";
  out.textContent = "";
  out.dataset.rawJson = "";
  if (statusContainer) statusContainer.style.display = "none";

  try {
    const response = await fetch("/internal/tick?format=text", { method: "POST" });
    const bodyText = await response.text();
    if (!response.ok) {
      throw new Error(`tick request failed with status ${response.status}\n${bodyText}`);
    }
    meta.textContent = "POST /internal/tick?format=text";
    out.textContent = bodyText || "(empty)";
  } catch (error) {
    meta.textContent = "failed";
    out.textContent = String(error);
  } finally {
    button.disabled = false;
    button.classList.remove("loading");
  }
}

async function runTick(btn, incremental = true) {
  const limit = document.getElementById("tick-limit-input")?.value || "100";
  await runInternalAsync("tick", btn, { incremental, limit });
}

async function runDiscovery(btn) {
  await runInternalAsync("discovery", btn);
}

async function runCareers(btn) {
  await runInternalAsync("careers", btn);
}

async function runGuess(btn) {
  await runInternalAsync("guess", btn);
}

async function runAtsReverse(btn) {
  await runInternalAsync("ats-reverse", btn);
}

async function runDorking(btn) {
  await runInternalAsync("dorking", btn);
}

async function runBackfillDepartment(btn) {
  await runInternalAsync("backfill-department", btn);
}

async function runBackfillCompliance(btn) {
  const limit = document.getElementById("backfill-limit-input")?.value || "10000";
  await runInternalAsync("backfill-compliance", btn, { limit });
}

async function runBackfillSalary(btn) {
  const limit = document.getElementById("backfill-limit-input")?.value || "10000";
  await runInternalAsync("backfill-salary", btn, { limit });
}

async function runForceSync(btn, companyAtsId) {
  await runInternal(`/internal/audit/ats-force-sync/${companyAtsId}`, btn);
}

async function deactivateAts(companyAtsId) {
  if (!confirm("Are you sure you want to deactivate this ATS integration?")) return;
  try {
    const response = await fetch(`/internal/audit/ats-deactivate/${companyAtsId}`, { method: 'POST' });
    if (!response.ok) throw new Error("Deactivation failed");
    await safeLoadAtsHealth();
  } catch (e) {
    alert(e.message);
  }
}

async function runPreviewJob(btn) {
  const provider = document.getElementById("preview-provider").value.trim();
  const slug = document.getElementById("preview-slug").value.trim();
  const jobId = document.getElementById("preview-job-id").value.trim();
  
  if (!provider || !slug) {
    alert("Provider and ATS Slug are required.");
    return;
  }
  
  const params = new URLSearchParams({ provider, slug });
  if (jobId) params.set("job_id", jobId);
  
  await runInternal(`/internal/preview-job?${params.toString()}`, btn, 'preview-cancel-btn');
}

let syncAbortController = null;

function cancelSync() {
  if (syncAbortController) {
    syncAbortController.abort();
  }
}

async function runInternal(url, btn, cancelBtnId = null) {
  const out = document.getElementById("tick-output");
  const meta = document.getElementById("tick-meta");
  const statusContainer = document.getElementById("task-status-container");
  const cancelBtn = cancelBtnId ? document.getElementById(cancelBtnId) : null;

  if (btn) {
    btn.disabled = true;
    btn.classList.add("loading");
  }
  if (cancelBtn) {
    cancelBtn.style.display = "inline-block";
  }
  
  meta.textContent = "running...";
  out.textContent = "";
  out.dataset.rawJson = "";
  if (statusContainer) statusContainer.style.display = "none";

  if (syncAbortController) {
    syncAbortController.abort();
  }
  syncAbortController = new AbortController();

  try {
    const response = await fetch(url, {
      method: "POST",
      credentials: "same-origin",
      signal: syncAbortController.signal
    });

    const text = await response.text();

    if (!response.ok) {
      throw new Error(text);
    }

    meta.textContent = url;
    out.textContent = text || "(ok)";
  } catch (err) {
    if (err.name === 'AbortError') {
      meta.textContent = "cancelled";
      out.textContent = "Request cancelled by user.";
    } else {
      meta.textContent = "error";
      out.textContent = String(err);
    }
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.classList.remove("loading");
    }
    if (cancelBtn) {
      cancelBtn.style.display = "none";
    }
    syncAbortController = null;
  }
}

function downloadOutput() {
  const outText = document.getElementById("tick-output").textContent;
  const rawJson = document.getElementById("tick-output").dataset.rawJson;
  if (!outText || outText === "No run yet." || outText === "Requesting...") {
    alert("No output available to download.");
    return;
  }
  
  let finalContent = "";
  if (rawJson) {
    finalContent += "--- TASK METADATA ---\n" + rawJson + "\n\n--- LIVE LOGS ---\n";
  }
  finalContent += outText;

  const blob = new Blob([finalContent], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `openjobseu-logs-${new Date().toISOString().replace(/[:.]/g, "-")}.log`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

document.getElementById("download-output-btn").addEventListener("click", downloadOutput);
document.addEventListener("keydown", (e) => {
  if (e.altKey && e.key.toLowerCase() === "d") {
    e.preventDefault();
    downloadOutput();
  }
      if (e.key === "Escape") {
        document.querySelectorAll('.job-row.selected').forEach(el => el.classList.remove('selected'));
        document.querySelectorAll('.details-row.open').forEach(el => el.classList.remove('open'));
      }
});

let currentTaskId = null;

async function cancelCurrentTask() {
  if (!currentTaskId) return;
  const btn = document.getElementById("cancel-task-btn");
  if (btn) {
      btn.disabled = true;
      btn.textContent = "Cancelling...";
  }
  try {
    const res = await fetch(`/internal/tasks/${currentTaskId}/cancel`, { method: "POST" });
    if (!res.ok) throw new Error(await res.text());
  } catch (err) {
    alert("Failed to cancel: " + err.message);
    if (btn) { btn.disabled = false; btn.textContent = "Cancel Task"; }
  }
}

async function runInternalAsync(taskName, btn, extraParams = {}) {
  const out = document.getElementById("tick-output");
  const meta = document.getElementById("tick-meta");
  const statusContainer = document.getElementById("task-status-container");
  const statusHeader = document.getElementById("task-status-header");
  const statusGrid = document.getElementById("task-status-grid");

  if (btn) {
    btn.disabled = true;
    btn.classList.add("loading");
  }
  meta.textContent = `starting async task: ${taskName}...`;
  out.textContent = "Requesting...";
  out.dataset.rawJson = "";
  if (statusContainer) statusContainer.style.display = "none";

  try {
    const urlParams = new URLSearchParams(extraParams);
    const queryStr = urlParams.toString() ? `?${urlParams.toString()}` : "";

    const response = await fetch(`/internal/tasks/${taskName}${queryStr}`, {
      method: "POST",
      credentials: "same-origin"
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(text);
    }

    const data = await response.json();
    const taskId = data.task_id;
    meta.textContent = `Task ${taskName} [${taskId}]`;
    currentTaskId = taskId;
    
    const cancelBtn = document.getElementById("cancel-task-btn");
    if (cancelBtn) {
      cancelBtn.style.display = "inline-block";
      cancelBtn.disabled = false;
      cancelBtn.textContent = "Cancel Task";
    }
    
    // Pokaż UI od razu po otrzymaniu ID zadania
    if (statusContainer) {
      statusContainer.style.display = "block";
      statusHeader.innerHTML = `<span class="task-status-badge pending">pending</span> <span style="font-size: 0.85rem; color: var(--muted);">ID: ${taskId}</span>`;
      const pBar = document.getElementById("task-progress-bar");
      if (pBar) {
        pBar.className = "progress-bar-fill pending";
      }
      statusGrid.innerHTML = "";
    }

    let attempt = 0;
    while (true) {
      attempt++;
      await new Promise(r => setTimeout(r, 2000));
      const statusRes = await fetch(`/internal/tasks/${taskId}`);
      if (!statusRes.ok) throw new Error("Failed to fetch task status");
      const statusData = await statusRes.json();

      const { logs, result, status, task, error, ...restData } = statusData;
      
      let displayStatus = status;
      if (status === 'running' && restData.cancel_requested) {
        displayStatus = 'cancelling';
      }
      
      if (statusContainer) {
        statusContainer.style.display = "block";
        statusHeader.innerHTML = `<span class="task-status-badge ${esc(displayStatus)}">${esc(displayStatus)}</span> <span style="font-size: 0.85rem; color: var(--muted);">Attempt: ${attempt} &bull; ID: ${taskId}</span>`;
        
        const pBar = document.getElementById("task-progress-bar");
        if (pBar) {
          pBar.className = `progress-bar-fill ${esc(displayStatus)}`;
        }
        
        let gridHtml = '';
        if (error) {
          gridHtml += `<div class="task-stat-card error-card"><strong>Error</strong><span style="font-size: 0.9rem; font-family: monospace;">${esc(error)}</span></div>`;
        }
        
        if (result !== undefined && result !== null) {
          if (typeof result === 'object') {
            for (const [k, v] of Object.entries(result)) {
              if (typeof v === 'object' && v !== null) {
                const valDisplay = esc(JSON.stringify(v, null, 2));
                gridHtml += `<div class="task-stat-card" style="grid-column: 1 / -1;"><strong>${esc(k)}</strong><pre class="json-dump" style="margin-top: 8px; max-height: 250px; overflow: auto; font-weight: normal; line-height: 1.4;">${valDisplay}</pre></div>`;
              } else {
                gridHtml += `<div class="task-stat-card"><strong>${esc(k)}</strong><span>${esc(String(v))}</span></div>`;
              }
            }
          } else {
            gridHtml += `<div class="task-stat-card"><strong>Result</strong><span>${esc(String(result))}</span></div>`;
          }
        }
        statusGrid.innerHTML = gridHtml;
      }

      const { logs: _l, ...pureJson } = statusData;
      out.dataset.rawJson = JSON.stringify(pureJson, null, 2);

      out.textContent = logs ? logs : "No logs emitted.";
      out.scrollTop = out.scrollHeight; // Auto-scroll to new logs

      if (["completed", "failed", "cancelled"].includes(statusData.status)) {
        meta.textContent = `Task ${taskName} [${taskId}] finished in ${attempt} attempts.`;
        if (cancelBtn) cancelBtn.style.display = "none";
        currentTaskId = null;
        break;
      }
    }
  } catch (err) {
    meta.textContent = "error";
    out.textContent = String(err);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.classList.remove("loading");
    }
  }
}

const compTopScrollWrap = document.getElementById("comp-top-scroll-wrap");
const compTableWrap = document.getElementById("comp-table-wrap");
if (compTopScrollWrap && compTableWrap) {
  compTopScrollWrap.addEventListener("scroll", () => { compTableWrap.scrollLeft = compTopScrollWrap.scrollLeft; });
  compTableWrap.addEventListener("scroll", () => { compTopScrollWrap.scrollLeft = compTableWrap.scrollLeft; });
}

function scheduleLoad() {
  if (debounceTimer) clearTimeout(debounceTimer);
  debounceTimer = setTimeout(safeLoadJobs, 250);
}

for (const id of ids) {
  const node = document.getElementById(id);
  if (!node) continue;
  node.addEventListener("input", scheduleLoad);
  node.addEventListener("change", scheduleLoad);
}

// Pagination bindings
document.getElementById("prev-btn").addEventListener("click", () => {
  const offsetEl = document.getElementById("offset");
  const limit = parseInt(document.getElementById("limit").value || "50", 10);
  let offset = parseInt(offsetEl.value || "0", 10);
  offsetEl.value = Math.max(0, offset - limit);
  safeLoadJobs();
});

document.getElementById("next-btn").addEventListener("click", () => {
  const offsetEl = document.getElementById("offset");
  const limit = parseInt(document.getElementById("limit").value || "50", 10);
  let offset = parseInt(document.getElementById("offset").value || "0", 10);
  offsetEl.value = offset + limit;
  safeLoadJobs();
});

// Clear filters binding
document.getElementById("clear-btn").addEventListener("click", () => {
  for (const id of ids) {
    const el = document.getElementById(id);
    if (!el) continue;
    el.value = (id === 'limit') ? "50" : (id === 'offset') ? "0" : "";
  }
  safeLoadJobs();
});

// Top scrollbar sync
const topScrollWrap = document.getElementById("top-scroll-wrap");
const mainTableWrap = document.getElementById("main-table-wrap");
if (topScrollWrap && mainTableWrap) {
  topScrollWrap.addEventListener("scroll", () => {
    mainTableWrap.scrollLeft = topScrollWrap.scrollLeft;
  });
  mainTableWrap.addEventListener("scroll", () => {
    topScrollWrap.scrollLeft = mainTableWrap.scrollLeft;
  });
}
function updateTopScrollbar() {
  const table = mainTableWrap?.querySelector("table");
  const dummy = document.getElementById("top-scroll-dummy");
  if (table && dummy) {
    dummy.style.width = table.offsetWidth + "px";
  }
  const cTable = compTableWrap?.querySelector("table");
  const cDummy = document.getElementById("comp-top-scroll-dummy");
  if (cTable && cDummy) cDummy.style.width = cTable.offsetWidth + "px";
}
window.addEventListener("resize", updateTopScrollbar);

document.getElementById("refresh-btn").addEventListener("click", safeLoadAll);
document.getElementById("tick-btn").addEventListener("click", runTickDev);

(async () => {
  const hostname = window.location.hostname;
  if (hostname.startsWith('openjobseu') && !hostname.startsWith('dev-')) {
    document.body.classList.add('is-prod');
  }
  renderJobColsMenu();
  renderCompColsMenu();
  renderJobHeaders();
  renderCompHeaders();
  try {
    await loadFilterRegistry();
  } catch (error) {
    const body = document.getElementById("rows");
    body.innerHTML = `<tr><td class="error" colspan="13">${esc(error.message)}</td></tr>`;
    return;
  }
  safeLoadAll();
})();