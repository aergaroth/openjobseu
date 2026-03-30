(() => {
  "use strict";

  const FEED_URL = "/feed.json";
  const DEBOUNCE_MS = 200;

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

  // Description text stored in a closure map — never in data-* attributes
  // to avoid HTML injection via untrusted feed content
  const descriptionMap = new WeakMap();

  let activeFilters = {
    search: "",
    departments: new Set(),
    salaryMin: null,
    salaryMax: null,
    includeNoSalary: true,
    sort: "newest",
  };

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
        const haystack = [j.title, j.company, j.source_department, j.remote_scope]
          .filter(Boolean).join(" ").toLowerCase();
        if (!haystack.includes(q)) return false;
      }
      // Department
      if (departments.size > 0 && !departments.has(j.source_department)) return false;
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
      if (job.source_department) {
        metaRow.appendChild(makeIconTag(ICON_DEPT, job.source_department));
      }

      card.appendChild(metaRow);

      // ── Description ──────────────────────────────────
      const fullText  = job.description || "";
      const shortText = fullText.length > 220 ? fullText.substring(0, 220) : fullText;
      const needsToggle = fullText.length > 220;

      const descEl = document.createElement("p");
      descEl.className = "job-description";
      descEl.appendChild(safeText(shortText + (needsToggle ? "…" : "")));

      // Store in WeakMap — not in DOM attributes
      descriptionMap.set(descEl, { full: fullText, short: shortText });

      card.appendChild(descEl);

      if (needsToggle) {
        const toggleBtn = document.createElement("button");
        toggleBtn.className = "job-description-toggle";
        toggleBtn.setAttribute("aria-expanded", "false");
        toggleBtn.appendChild(safeText("Show more"));

        toggleBtn.addEventListener("click", () => {
          const data = descriptionMap.get(descEl);
          const expanded = toggleBtn.getAttribute("aria-expanded") === "true";
          descEl.textContent = "";
          descEl.appendChild(safeText(expanded ? data.short + "…" : data.full));
          toggleBtn.textContent = "";
          toggleBtn.appendChild(safeText(expanded ? "Show more" : "Show less"));
          toggleBtn.setAttribute("aria-expanded", String(!expanded));
        });

        card.appendChild(toggleBtn);
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
        btn.appendChild(safeText(`${d.name} (${d.count})`));
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
      "description": j.description || "",
      "employmentType": "FULL_TIME",
      ...(j.url ? { "url": j.url } : {}),
      ...(j.salary_min_eur || j.salary_max_eur ? {
        "baseSalary": {
          "@type": "MonetaryAmount",
          "currency": "EUR",
          "value": {
            "@type": "QuantitativeValue",
            "minValue": j.salary_min_eur || undefined,
            "maxValue": j.salary_max_eur || undefined,
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
