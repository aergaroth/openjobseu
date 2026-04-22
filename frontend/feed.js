(() => {
  "use strict";

  const FEED_URL = "/feed.json";
  const MARKET_STATS_URL = "/market-stats.json";
  const MARKET_SEGMENTS_URL = "/market-segments.json";
  const DEBOUNCE_MS = 200;

  const SEGMENT_TYPE_LABELS = {
    job_family: "By department",
    seniority:  "By seniority",
    country:    "By scope",
  };

  const JOB_FAMILY_LABELS = {
    software_development: "Engineering",
    data_science:         "Data & AI",
    design:               "Design",
    product_management:   "Product",
    marketing:            "Marketing",
    sales:                "Sales",
    hr:                   "People & HR",
    finance:              "Finance",
    operations:           "Operations",
  };

  const COUNTRY_LABELS = {
    "Home Based - Emea": "Remote - Emea",
    "Home Based - EMEA": "Remote - Emea",
  };

  const _AMERICAS_RE = /americ|apac|latam/i;

  // ── DOM refs ───────────────────────────────────────────
  const metaEl               = document.getElementById("meta");
  const jobsList             = document.getElementById("jobs-list");
  const searchEl             = document.getElementById("search");
  const deptFiltersEl        = document.getElementById("department-filters");
  const salaryMinEl          = document.getElementById("salary-min");
  const salaryMaxEl          = document.getElementById("salary-max");
  const salaryIncludeUnknown = document.getElementById("salary-include-unknown");
  const resetBtn             = document.getElementById("reset-filters");
  const sortSelect           = document.getElementById("sort-select");
  const resultsCountEl       = document.getElementById("results-count");
  const structuredDataEl     = document.getElementById("structured-data");

  if (!jobsList) return;

  // ── State ──────────────────────────────────────────────
  let allJobs = [];

  let activeFilters = {
    search: "",
    departments: new Set(),
    salaryMin: null,
    salaryMax: null,
    includeNoSalary: true,
    sort: "newest",
  };

  // ── Markdown renderer ──────────────────────────────────
  // Converts a safe subset of Markdown to HTML.
  // Text portions are HTML-escaped before insertion; only whitelisted
  // tags are ever produced. Safe for use with innerHTML.
  function renderMarkdown(text) {
    if (!text) return '';

    function esc(s) {
      return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function safeHref(url) {
      // url arrives pre-HTML-escaped; strip entities before URL validation
      const raw = url.replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"');
      try {
        const u = new URL(raw);
        return (u.protocol === 'http:' || u.protocol === 'https:') ? esc(raw) : '#';
      } catch { return '#'; }
    }

    // Inline markup: runs on already-HTML-escaped text
    function inline(s) {
      return esc(s)
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g,     '<em>$1</em>')
        .replace(/`(.+?)`/g,       '<code>$1</code>')
        .replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_, label, url) =>
          `<a href="${safeHref(url)}" target="_blank" rel="noopener noreferrer">${label}</a>`
        );
    }

    const lines = text.split('\n');
    const blocks = [];
    let i = 0;

    while (i < lines.length) {
      const trimmed = lines[i].trim();

      // ATX headings — rendered as h4–h6 to stay below the page's h1/h2 hierarchy
      const hm = trimmed.match(/^(#{1,3})\s+(.*)/);
      if (hm) {
        const lvl = hm[1].length + 3;
        blocks.push(`<h${lvl} class="md-h">${inline(hm[2])}</h${lvl}>`);
        i++; continue;
      }

      // Unordered list
      if (/^[-*+] /.test(trimmed)) {
        const items = [];
        while (i < lines.length && /^[-*+] /.test(lines[i].trim())) {
          items.push(`<li>${inline(lines[i].trim().slice(2))}</li>`);
          i++;
        }
        blocks.push(`<ul>${items.join('')}</ul>`);
        continue;
      }

      // Ordered list
      if (/^\d+\. /.test(trimmed)) {
        const items = [];
        while (i < lines.length && /^\d+\. /.test(lines[i].trim())) {
          items.push(`<li>${inline(lines[i].trim().replace(/^\d+\.\s+/, ''))}</li>`);
          i++;
        }
        blocks.push(`<ol>${items.join('')}</ol>`);
        continue;
      }

      // Blank line
      if (!trimmed) { i++; continue; }

      // Paragraph — collect consecutive non-block lines
      const paraLines = [];
      while (
        i < lines.length &&
        lines[i].trim() &&
        !/^#{1,3} /.test(lines[i].trim()) &&
        !/^[-*+] /.test(lines[i].trim()) &&
        !/^\d+\. /.test(lines[i].trim())
      ) {
        paraLines.push(lines[i].trim());
        i++;
      }
      blocks.push(`<p>${paraLines.map(inline).join('<br>')}</p>`);
    }

    return blocks.join('');
  }

  // ── Helpers ────────────────────────────────────────────
  function debounce(fn, ms) {
    let t;
    return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
  }

  function safeText(str) {
    // Returns a text node — never parsed as HTML
    return document.createTextNode(str ?? "");
  }

  function el(tag, attrs = {}, children = []) {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (k === "class")        node.className = v;
      else if (k === "href")    node.href = v;
      else if (k === "target")  node.target = v;
      else if (k === "rel")     node.rel = v;
      else if (k === "aria-hidden") node.setAttribute("aria-hidden", v);
      else                      node.setAttribute(k, v);
    }
    for (const child of children) {
      if (typeof child === "string") node.appendChild(safeText(child));
      else if (child)               node.appendChild(child);
    }
    return node;
  }

  function formatSalary(job) {
    if (!job.salary_min && !job.salary_max) return null;
    const currency = job.salary_currency || "EUR";
    const fmt = n => Number(n).toLocaleString("en-EU", { maximumFractionDigits: 0 });
    if (job.salary_min && job.salary_max)
      return `${fmt(job.salary_min)} – ${fmt(job.salary_max)} ${currency}`;
    return `${fmt(job.salary_min || job.salary_max)} ${currency}`;
  }

  function formatDate(iso) {
    if (!iso) return "";
    return new Date(iso).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
  }

  // Icon SVG — inline, aria-hidden, no emoji
  const ICON_DATE = `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true" focusable="false"><rect x="2" y="3" width="12" height="11" rx="1.5"/><path d="M5 1v4M11 1v4M2 7h12"/></svg>`;
  const ICON_PIN  = `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true" focusable="false"><path d="M8 1.5C5.79 1.5 4 3.29 4 5.5c0 3.25 4 9 4 9s4-5.75 4-9c0-2.21-1.79-4-4-4z"/><circle cx="8" cy="5.5" r="1.5"/></svg>`;
  const ICON_DEPT = `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true" focusable="false"><rect x="1" y="5" width="14" height="9" rx="1.5"/><path d="M5 5V3.5A1.5 1.5 0 016.5 2h3A1.5 1.5 0 0111 3.5V5"/></svg>`;

  function makeIconTag(iconHtml, text) {
    const span = document.createElement("span");
    span.className = "job-tag";
    span.innerHTML = iconHtml; // only trusted SVG strings, not user data
    span.appendChild(safeText(text));
    return span;
  }

  // ── Render ─────────────────────────────────────────────
  function applySort(jobs) {
    const sorted = [...jobs];
    switch (activeFilters.sort) {
      case "newest":
        return sorted.sort((a, b) => new Date(b.first_seen_at) - new Date(a.first_seen_at));
      case "oldest":
        return sorted.sort((a, b) => new Date(a.first_seen_at) - new Date(b.first_seen_at));
      case "salary-desc":
        return sorted.sort((a, b) => (b.salary_max_eur || b.salary_min_eur || 0) - (a.salary_max_eur || a.salary_min_eur || 0));
      case "salary-asc":
        return sorted.sort((a, b) => {
          const av = a.salary_min_eur || a.salary_max_eur || Infinity;
          const bv = b.salary_min_eur || b.salary_max_eur || Infinity;
          return av - bv;
        });
      default:
        return sorted;
    }
  }

  function filterJobs() {
    const { search, departments, salaryMin, salaryMax, includeNoSalary } = activeFilters;
    const q = search.toLowerCase();
    return allJobs.filter(j => {
      // Text search: title, company, department, remote_scope
      if (q) {
        const haystack = [j.title, j.company, j.source_department, j.remote_scope,
          j.job_family ? JOB_FAMILY_LABELS[j.job_family] : null]
          .filter(Boolean).join(" ").toLowerCase();
        if (!haystack.includes(q)) return false;
      }
      // Department
      if (departments.size > 0 && !departments.has(j.job_family)) return false;
      // Salary
      if (salaryMin !== null || salaryMax !== null) {
        const hasSalary = j.salary_min_eur || j.salary_max_eur;
        if (!hasSalary) return includeNoSalary;
        const jobMin = j.salary_min_eur || j.salary_max_eur;
        const jobMax = j.salary_max_eur || j.salary_min_eur;
        if (salaryMin !== null && jobMax < salaryMin) return false;
        if (salaryMax !== null && jobMin > salaryMax) return false;
      }
      return true;
    });
  }

  function renderJobs() {
    const filtered = applySort(filterJobs());

    // Update live region count
    if (resultsCountEl) {
      resultsCountEl.textContent = filtered.length === allJobs.length
        ? `${allJobs.length} jobs`
        : `${filtered.length} of ${allJobs.length} jobs`;
    }

    jobsList.innerHTML = "";

    if (filtered.length === 0) {
      const p = document.createElement("div");
      p.className = "placeholder-row";
      p.setAttribute("role", "status");
      p.appendChild(safeText("No jobs match your filters."));
      jobsList.appendChild(p);
      return;
    }

    const fragment = document.createDocumentFragment();

    filtered.forEach((job, i) => {
      const card = document.createElement("article");
      card.className = "job-card loaded";
      card.style.animationDelay = `${Math.min(i * 15, 250)}ms`;
      card.setAttribute("aria-label", `${job.title} at ${job.company}`);

      // ── Top row ─────────────────────────────────────
      const topRow = document.createElement("div");
      topRow.className = "job-card-top";

      const titleWrap = document.createElement("div");
      titleWrap.className = "job-title-wrap";

      const titleEl = document.createElement("h2");
      titleEl.className = "job-title";

      const titleLink = document.createElement("a");
      titleLink.href = job.url || "#";
      titleLink.target = "_blank";
      titleLink.rel = "noopener noreferrer";
      titleLink.appendChild(safeText(job.title));
      titleEl.appendChild(titleLink);
      titleWrap.appendChild(titleEl);

      const companyEl = document.createElement("div");
      companyEl.className = "job-company";
      companyEl.appendChild(safeText(job.company));
      titleWrap.appendChild(companyEl);

      topRow.appendChild(titleWrap);

      const salaryStr = formatSalary(job);
      if (salaryStr) {
        const salaryEl = document.createElement("div");
        salaryEl.className = "job-salary";
        salaryEl.setAttribute("aria-label", `Salary: ${salaryStr}`);
        salaryEl.appendChild(safeText(salaryStr));
        topRow.appendChild(salaryEl);
      }

      card.appendChild(topRow);

      // ── Meta tags ────────────────────────────────────
      const metaRow = document.createElement("div");
      metaRow.className = "job-meta";
      metaRow.setAttribute("aria-label", "Job details");

      if (job.first_seen_at) {
        metaRow.appendChild(makeIconTag(ICON_DATE, formatDate(job.first_seen_at)));
      }
      if (job.remote_scope) {
        metaRow.appendChild(makeIconTag(ICON_PIN, job.remote_scope));
      }
      if (job.job_family && JOB_FAMILY_LABELS[job.job_family]) {
        metaRow.appendChild(makeIconTag(ICON_DEPT, JOB_FAMILY_LABELS[job.job_family]));
      }

      card.appendChild(metaRow);

      // ── Description ──────────────────────────────────
      // CSS max-height clips the text; JS only toggles .expanded.
      const fullText = job.description || "";
      const CLIP_THRESHOLD = 160;

      const descEl = document.createElement("div");
      descEl.className = "job-description";
      descEl.innerHTML = renderMarkdown(fullText);
      card.appendChild(descEl);

      if (fullText.length > CLIP_THRESHOLD) {
        const toggleBtn = document.createElement("button");
        toggleBtn.className = "job-description-toggle";
        toggleBtn.setAttribute("aria-expanded", "false");
        toggleBtn.appendChild(safeText("Show more"));

        toggleBtn.addEventListener("click", () => {
          const expanded = toggleBtn.getAttribute("aria-expanded") === "true";
          descEl.classList.toggle("expanded", !expanded);
          toggleBtn.setAttribute("aria-expanded", String(!expanded));
          toggleBtn.textContent = "";
          toggleBtn.appendChild(safeText(expanded ? "Show more" : "Show less"));
        });

        card.appendChild(toggleBtn);
      }

      if (job.source_department) {
        const deptDetail = document.createElement("div");
        deptDetail.className = "job-source-dept";
        deptDetail.appendChild(safeText(job.source_department));
        card.appendChild(deptDetail);
      }

      fragment.appendChild(card);
    });

    jobsList.appendChild(fragment);
  }

  function renderDepartments(departments) {
    if (!deptFiltersEl) return;
    deptFiltersEl.innerHTML = "";

    departments
      .sort((a, b) => b.count - a.count)
      .forEach(d => {
        const btn = document.createElement("button");
        btn.className = "dept-btn";
        btn.setAttribute("aria-pressed", "false");
        btn.dataset.dept = d.name;
        const label = JOB_FAMILY_LABELS[d.name] || d.name;
        btn.appendChild(safeText(`${label} (${d.count})`));
        deptFiltersEl.appendChild(btn);
      });
  }

  // ── Structured data (JSON-LD) ──────────────────────────
  function injectStructuredData(jobs) {
    if (!structuredDataEl || !jobs.length) return;
    const listings = jobs.slice(0, 50).map(j => ({
      "@type": "JobPosting",
      "title": j.title,
      "hiringOrganization": { "@type": "Organization", "name": j.company },
      "jobLocationType": "TELECOMMUTE",
      "applicantLocationRequirements": { "@type": "Country", "name": "Europe" },
      "datePosted": j.first_seen_at ? j.first_seen_at.substring(0, 10) : undefined,
      "validThrough": (() => {
        const base = j.last_seen_at || j.first_seen_at;
        if (!base) return undefined;
        const d = new Date(base);
        d.setDate(d.getDate() + 30);
        return d.toISOString().substring(0, 10);
      })(),
      "description": j.description || "",
      "employmentType": "FULL_TIME",
      ...(j.url ? { "url": j.url } : {}),
      ...(j.salary_min_eur != null && j.salary_max_eur != null ? {
        "baseSalary": {
          "@type": "MonetaryAmount",
          "currency": "EUR",
          "value": {
            "@type": "QuantitativeValue",
            "minValue": j.salary_min_eur,
            "maxValue": j.salary_max_eur,
            "unitText": "YEAR"
          }
        }
      } : {})
    }));

    structuredDataEl.textContent = JSON.stringify({
      "@context": "https://schema.org",
      "@graph": listings
    });
  }

  // ── Event listeners ────────────────────────────────────
  function setupEventListeners() {
    const debouncedSearch = debounce(v => {
      activeFilters.search = v;
      renderJobs();
    }, DEBOUNCE_MS);

    searchEl?.addEventListener("input", e => debouncedSearch(e.target.value.trim()));

    deptFiltersEl?.addEventListener("click", e => {
      const btn = e.target.closest(".dept-btn");
      if (!btn) return;
      const dept = btn.dataset.dept;
      const isActive = activeFilters.departments.has(dept);
      if (isActive) {
        activeFilters.departments.delete(dept);
        btn.classList.remove("active");
        btn.setAttribute("aria-pressed", "false");
      } else {
        activeFilters.departments.add(dept);
        btn.classList.add("active");
        btn.setAttribute("aria-pressed", "true");
      }
      renderJobs();
    });

    const debouncedSalary = debounce(() => {
      activeFilters.salaryMin = salaryMinEl?.value ? parseInt(salaryMinEl.value, 10) : null;
      activeFilters.salaryMax = salaryMaxEl?.value ? parseInt(salaryMaxEl.value, 10) : null;
      renderJobs();
    }, DEBOUNCE_MS);

    salaryMinEl?.addEventListener("input", debouncedSalary);
    salaryMaxEl?.addEventListener("input", debouncedSalary);

    salaryIncludeUnknown?.addEventListener("change", e => {
      activeFilters.includeNoSalary = e.target.checked;
      renderJobs();
    });

    sortSelect?.addEventListener("change", e => {
      activeFilters.sort = e.target.value;
      renderJobs();
    });

    resetBtn?.addEventListener("click", () => {
      activeFilters = {
        search: "",
        departments: new Set(),
        salaryMin: null,
        salaryMax: null,
        includeNoSalary: true,
        sort: "newest",
      };
      if (searchEl)  { searchEl.value = ""; }
      if (salaryMinEl) { salaryMinEl.value = ""; }
      if (salaryMaxEl) { salaryMaxEl.value = ""; }
      if (sortSelect)  { sortSelect.value = "newest"; }
      if (salaryIncludeUnknown) { salaryIncludeUnknown.checked = true; }
      deptFiltersEl?.querySelectorAll(".dept-btn").forEach(b => {
        b.classList.remove("active");
        b.setAttribute("aria-pressed", "false");
      });
      renderJobs();
      searchEl?.focus();
    });
  }

  // ── Market breakdown ───────────────────────────────────

  function renderBreakdownPanel(title, items, labelMap, segType) {
    if (!items || items.length === 0) return null;

    let displayItems;
    if (segType === "country") {
      // Normalize "Home Based - X" labels for any data stored before the pipeline fix
      items = items.map(i => ({
        ...i,
        value: i.value.replace(/^home\s+based\s*[-–]\s*/i, "Remote - "),
      }));
      // Remove Americas/APAC entries
      items = items.filter(i => !_AMERICAS_RE.test(i.value));
      // Remove plain country name if a "(Remote)" variant exists
      const hasRemote = new Set(
        items
          .filter(i => i.value.endsWith(" (Remote)"))
          .map(i => i.value.slice(0, -" (Remote)".length))
      );
      items = items.filter(i => !hasRemote.has(i.value));

      const nonEu = items.find(i => i.value === "Non EU");
      const euItems = items.filter(i => i.value !== "Non EU").slice(0, 7);
      displayItems = nonEu ? [...euItems, nonEu] : euItems;
    } else {
      displayItems = items.slice(0, 8);
    }

    const maxActive = Math.max(...displayItems.map(i => i.jobs_active));

    const panel = el("div", { class: "breakdown-panel" });
    panel.appendChild(el("h3", { class: "breakdown-panel-title" }, [title]));

    const list = el("ul", { class: "breakdown-list", role: "list" });
    displayItems.forEach(item => {
      const label = (labelMap && labelMap[item.value]) || item.value.replace(/_/g, " ");
      const pct = maxActive > 0 ? Math.round((item.jobs_active / maxActive) * 100) : 0;
      const salaryK = item.median_salary_eur ? Math.round(item.median_salary_eur / 1000) : 0;
      const salaryReliable = salaryK > 0
        && (item.salary_count || 0) >= 3
        && item.jobs_active > 0
        && (item.salary_count / item.jobs_active) >= 0.25;
      const salary = salaryReliable ? `€${salaryK}k` : null;

      const row = el("li", { class: "breakdown-row" });
      const labelEl = el("span", { class: "breakdown-label" }, [label]);
      const barWrap = el("div", { class: "breakdown-bar-wrap" }, [
        el("div", { class: "breakdown-bar", style: `width:${pct}%` }),
      ]);
      const count = el("span", { class: "breakdown-count" }, [`${item.jobs_active}`]);
      row.appendChild(labelEl);
      row.appendChild(barWrap);
      row.appendChild(count);
      if (salary) {
        row.appendChild(el("span", { class: "breakdown-salary", title: "Median salary" }, [salary]));
      }
      list.appendChild(row);
    });

    panel.appendChild(list);
    return panel;
  }

  function renderMarketBreakdown(data) {
    const section = document.getElementById("market-breakdown");
    const grid = document.getElementById("breakdown-grid");
    if (!section || !grid) return;

    const ORDER = ["job_family", "seniority", "country"];
    let rendered = 0;

    ORDER.forEach(segType => {
      const items = data.segments[segType];
      if (!items || items.length === 0) return;

      const labelMap = segType === "job_family" ? JOB_FAMILY_LABELS
                     : segType === "country"    ? COUNTRY_LABELS
                     : null;
      const title = SEGMENT_TYPE_LABELS[segType] || segType;
      const panel = renderBreakdownPanel(title, items, labelMap, segType);
      if (panel) {
        grid.appendChild(panel);
        rendered++;
      }
    });

    if (rendered > 0) section.removeAttribute("hidden");
  }

  function loadMarketSegments(baseUrl = "") {
    fetch(`${baseUrl}${MARKET_SEGMENTS_URL}`)
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(data => renderMarketBreakdown(data))
      .catch(err => console.error("Market segments error:", err));
  }

  // ── Market stats ───────────────────────────────────────

  function computeMetrics(stats, days) {
    const subset = stats.slice(-days);
    const last = subset[subset.length - 1];
    const totalActive = last ? last.jobs_active : 0;

    const salaryVals = subset.map(s => s.median_salary_eur).filter(v => v != null);
    const medianSalary = salaryVals.length
      ? salaryVals.reduce((a, b) => a + b, 0) / salaryVals.length
      : null;

    const remoteVals = subset.map(s => s.remote_ratio).filter(v => v != null);
    const remoteRatio = remoteVals.length
      ? remoteVals.reduce((a, b) => a + b, 0) / remoteVals.length
      : null;

    return { totalActive, medianSalary, remoteRatio };
  }

  function setChartPeriod(days, data) {
    const base = data.meta.chart_base_url;
    const volumeImg = document.getElementById("chart-volume");
    const salaryImg = document.getElementById("chart-salary");
    const remoteImg = document.getElementById("chart-remote");

    if (volumeImg) volumeImg.src = `${base}/charts/volume-${days}d.svg`;
    if (salaryImg) salaryImg.src = `${base}/charts/salary-${days}d.svg`;
    if (remoteImg) remoteImg.src = `${base}/charts/remote-${days}d.svg`;

    document.querySelectorAll(".toggle-btn").forEach(btn => {
      const pressed = parseInt(btn.dataset.days, 10) === days;
      btn.classList.toggle("active", pressed);
      btn.setAttribute("aria-pressed", String(pressed));
    });
  }

  function renderMarketError() {
    const body = document.getElementById("market-body");
    if (!body) return;
    body.textContent = "";
    body.appendChild(safeText("Statistics unavailable."));
  }

  function renderMarketOverview(data) {
    const section = document.getElementById("market-overview");
    if (!section) return;

    // Metric cards
    const cardsEl = section.querySelector(".metric-cards");
    if (cardsEl) {
      const m = computeMetrics(data.stats, 7);
      const jobsTotal    = data.meta.jobs_total    ?? null;
      const jobsApproved = data.meta.jobs_approved ?? null;
      cardsEl.innerHTML = "";
      [
        { label: "Total active",       value: jobsTotal    != null ? jobsTotal.toLocaleString() : "—" },
        { label: "In feed (approved)", value: jobsApproved != null && jobsTotal != null
            ? `${jobsApproved.toLocaleString()} of ${jobsTotal.toLocaleString()}`
            : jobsApproved != null ? jobsApproved.toLocaleString() : "—" },
        { label: "Median annual salary", value: m.medianSalary != null ? `€${Math.round(m.medianSalary).toLocaleString()}/yr` : "—" },
        { label: "Remote jobs",        value: m.remoteRatio != null ? `${Math.round(m.remoteRatio * 100)}% of active` : "—" },
      ].forEach(({ label, value }) => {
        cardsEl.appendChild(
          el("div", { class: "metric-card" }, [
            el("span", { class: "metric-card-label" }, [label]),
            el("div",  { class: "metric-card-value" }, [value]),
          ])
        );
      });
    }

    // Initial chart period
    setChartPeriod(7, data);

    // Toggle buttons
    section.querySelectorAll(".toggle-btn").forEach(btn => {
      btn.addEventListener("click", () => setChartPeriod(parseInt(btn.dataset.days, 10), data));
    });

    // Collapse button
    const collapseBtn = section.querySelector(".market-collapse");
    const body = document.getElementById("market-body");
    if (collapseBtn && body) {
      collapseBtn.addEventListener("click", () => {
        const expanded = collapseBtn.getAttribute("aria-expanded") === "true";
        body.hidden = expanded;
        collapseBtn.setAttribute("aria-expanded", String(!expanded));
        collapseBtn.textContent = "";
        collapseBtn.appendChild(safeText(expanded ? "Show" : "Hide"));
      });
    }

    section.removeAttribute("hidden");
  }

  function loadMarketStats(baseUrl = "") {
    fetch(`${baseUrl}${MARKET_STATS_URL}`)
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(data => renderMarketOverview(data))
      .catch(err => {
        console.error("Market stats error:", err);
        renderMarketError();
      });
  }

  // ── Fetch ──────────────────────────────────────────────
  fetch(FEED_URL)
    .then(r => {
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return r.json();
    })
    .then(data => {
      if (!data.jobs?.length) {
        jobsList.innerHTML = "";
        const p = document.createElement("div");
        p.className = "placeholder-row";
        p.setAttribute("role", "status");
        p.appendChild(safeText("No jobs available at the moment."));
        jobsList.appendChild(p);
        if (metaEl) metaEl.appendChild(safeText("Feed empty."));
        return;
      }

      allJobs = data.jobs;

      renderJobs();
      renderDepartments(data.meta?.departments || []);
      injectStructuredData(allJobs);
      setupEventListeners();
      loadMarketStats();
      loadMarketSegments();

      if (metaEl && data.meta?.generated_at) {
        const generated = new Date(data.meta.generated_at);
        const dateStr = generated.toLocaleString("en-GB", {
          day: "2-digit", month: "short", year: "numeric",
          hour: "2-digit", minute: "2-digit"
        });
        metaEl.textContent = "";
        metaEl.appendChild(safeText(`Updated ${dateStr}`));
        const br1 = document.createElement("br");
        const br2 = document.createElement("br");
        metaEl.appendChild(br1);
        metaEl.appendChild(br2);
        metaEl.appendChild(safeText(`${data.meta.count ?? allJobs.length} jobs in feed`));
      }
    })
    .catch(err => {
      console.error("Feed error:", err);
      jobsList.innerHTML = "";
      const p = document.createElement("div");
      p.className = "placeholder-row";
      p.setAttribute("role", "alert");
      p.appendChild(safeText("Feed temporarily unavailable. Please try again later."));
      jobsList.appendChild(p);
      if (metaEl) metaEl.appendChild(safeText("Feed unavailable."));
    });
})();
