const ids = [
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

function renderCountMap(nodeId, counts) {
  const node = document.getElementById(nodeId);
  if (!node) return;
  const entries = Object.entries(counts || {});
  if (entries.length === 0) {
    node.innerHTML = '<span class="chip">none</span>';
    return;
  }
  node.innerHTML = entries
    .map(([key, value]) => `<span class="chip">${esc(key)}: ${esc(value)}</span>`)
    .join("");
}

function toggleJobRow(row) {
  const isSelected = row.classList.contains('selected');
  
  document.querySelectorAll('.job-row.selected').forEach(el => el.classList.remove('selected'));
  document.querySelectorAll('.details-row.open').forEach(el => el.classList.remove('open'));
  
  if (!isSelected) {
    row.classList.add('selected');
    if (row.nextElementSibling) row.nextElementSibling.classList.add('open');
  }
}

function renderRows(items) {
  const body = document.getElementById("rows");
  if (!body) return;
  if (!items || items.length === 0) {
    body.innerHTML = '<tr><td colspan="13">No jobs found for current filter.</td></tr>';
    return;
  }
  body.innerHTML = items.map((job) => {
    const url = esc(job.source_url || "");
    const label = url ? "open" : "";
    const jobJson = esc(JSON.stringify(job, null, 2));
    return `
      <tr class="job-row" onclick="toggleJobRow(this)" title="Click to view raw JSON">
        <td class="mono">${esc(job.job_id)}</td>
        <td>${esc(job.source)}</td>
        <td>${esc(job.title)}</td>
        <td>${esc(job.company_name)}</td>
        <td>${esc(job.source_department)}</td>
        <td>${esc(job.status)}</td>
        <td>${esc(job.remote_class)}</td>
        <td>${esc(job.geo_class)}</td>
        <td>${esc(job.compliance_status)}</td>
        <td>${esc(job.compliance_score)}</td>
        <td class="mono">${esc(job.first_seen_at)}</td>
        <td class="mono">${esc(job.last_seen_at)}</td>
        <td>${url ? `<a href="${url}" target="_blank" rel="noreferrer" onclick="event.stopPropagation()">${label}</a>` : ""}</td>
      </tr>
      <tr class="details-row">
        <td colspan="13">
          <pre class="json-dump">${jobJson}</pre>
        </td>
      </tr>
    `;
  }).join("");
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
  renderRows(data.items || []);
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

  renderCompanyStatsRows(companyPayload.items || []);
  renderSourceStatsRows(sourcePayload.items || []);

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
  await Promise.all([safeLoadJobs(), safeLoadAuditStats(), safeLoadMetrics(), safeLoadAtsHealth()]);
}

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

async function runTick(btn) {
  await runInternal("/internal/tick?format=text", btn);
}

async function runTickIngestion(btn) {
  await runInternal("/internal/tick?format=text&group=ingestion", btn);
}

async function runTickMaintenance(btn) {
  await runInternal("/internal/tick?format=text&group=maintenance", btn);
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

async function runBackfillDepartment(btn) {
  await runInternalAsync("backfill-department", btn);
}

async function runBackfillCompliance(btn) {
  await runInternalAsync("backfill-compliance", btn);
}

async function runBackfillSalary(btn) {
  await runInternalAsync("backfill-salary", btn);
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

async function runInternal(url, btn) {
  const out = document.getElementById("tick-output");
  const meta = document.getElementById("tick-meta");
  const statusContainer = document.getElementById("task-status-container");

  if (btn) {
    btn.disabled = true;
    btn.classList.add("loading");
  }
  meta.textContent = "running...";
  out.textContent = "";
  out.dataset.rawJson = "";
  if (statusContainer) statusContainer.style.display = "none";

  try {
    const response = await fetch(url, {
      method: "POST",
      credentials: "same-origin"
    });

    const text = await response.text();

    if (!response.ok) {
      throw new Error(text);
    }

    meta.textContent = url;
    out.textContent = text || "(ok)";
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

async function runInternalAsync(taskName, btn) {
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
    const response = await fetch(`/internal/tasks/${taskName}`, {
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

    let attempt = 0;
    while (true) {
      attempt++;
      await new Promise(r => setTimeout(r, 2000));
      const statusRes = await fetch(`/internal/tasks/${taskId}`);
      if (!statusRes.ok) throw new Error("Failed to fetch task status");
      const statusData = await statusRes.json();

      const { logs, result, status, task, error, ...restData } = statusData;
      
      if (statusContainer) {
        statusContainer.style.display = "block";
        statusHeader.innerHTML = `<span class="task-status-badge ${esc(status)}">${esc(status)}</span> <span style="font-size: 0.85rem; color: var(--muted);">Attempt: ${attempt} &bull; ID: ${taskId}</span>`;
        
        let gridHtml = '';
        if (error) {
          gridHtml += `<div class="task-stat-card error-card"><strong>Error</strong><span style="font-size: 0.9rem; font-family: monospace;">${esc(error)}</span></div>`;
        }
        
        if (result !== undefined && result !== null) {
          if (typeof result === 'object') {
            for (const [k, v] of Object.entries(result)) {
              const valDisplay = (typeof v === 'object' && v !== null) ? esc(JSON.stringify(v)) : esc(String(v));
              gridHtml += `<div class="task-stat-card"><strong>${esc(k)}</strong><span>${valDisplay}</span></div>`;
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
      out.scrollTop = out.scrollHeight; // Auto-scroll do nowych logów

      if (statusData.status === "completed" || statusData.status === "failed") {
        meta.textContent = `Task ${taskName} [${taskId}] finished in ${attempt} attempts.`;
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
}
window.addEventListener("resize", updateTopScrollbar);

document.getElementById("refresh-btn").addEventListener("click", safeLoadAll);
document.getElementById("tick-btn").addEventListener("click", runTickDev);

(async () => {
  try {
    await loadFilterRegistry();
  } catch (error) {
    const body = document.getElementById("rows");
    body.innerHTML = `<tr><td class="error" colspan="13">${esc(error.message)}</td></tr>`;
    return;
  }
  safeLoadAll();
})();