(() => {
  const FEED_URL = "/feed.json";

  const metaEl = document.getElementById("meta");
  const jobsList = document.getElementById("jobs-list");
  const searchEl = document.getElementById("search");
  const departmentFiltersEl = document.getElementById("department-filters");
  const salaryMinEl = document.getElementById("salary-min");
  const salaryMaxEl = document.getElementById("salary-max");
  const resetFiltersEl = document.getElementById("reset-filters");

  if (!jobsList) return;

  let allJobs = [];
  let activeFilters = {
    search: "",
    departments: new Set(),
    salaryMin: null,
    salaryMax: null,
  };

  // ── Render ──────────────────────────────────────────────────
  function formatSalary(job) {
    if (!job.salary_min && !job.salary_max) return "";
    const min = job.salary_min;
    const max = job.salary_max;
    const currency = job.salary_currency || "";
    if (min && max) return `${min} - ${max} ${currency}`;
    return `${min || max} ${currency}`;
  }

  function renderJobs() {
    const { search, departments, salaryMin, salaryMax } = activeFilters;
    const searchQ = search.toLowerCase();

    const filteredJobs = allJobs.filter(j => {
      // Text search
      const matchesSearch = searchQ ? j.title.toLowerCase().includes(searchQ) || j.company.toLowerCase().includes(searchQ) : true;
      // Department filter
      const matchesDept = departments.size > 0 ? departments.has(j.source_department) : true;
      // Salary filter
      let matchesSalary = true;
      if (salaryMin || salaryMax) {
        if (!j.salary_min_eur && !j.salary_max_eur) {
          matchesSalary = false;
        } else {
          const jobMin = j.salary_min_eur || j.salary_max_eur;
          const jobMax = j.salary_max_eur || j.salary_min_eur;
          const filterMin = salaryMin || 0;
          const filterMax = salaryMax || Infinity;
          matchesSalary = jobMax >= filterMin && jobMin <= filterMax;
        }
      }
      return matchesSearch && matchesDept && matchesSalary;
    });

    jobsList.innerHTML = "";
    if (filteredJobs.length === 0) {
      jobsList.innerHTML = `<div class="placeholder-row">No jobs match your filters.</div>`;
      return;
    }

    const fragment = document.createDocumentFragment();
    filteredJobs.forEach((job, i) => {
      const card = document.createElement("div");
      card.className = "job-card loaded";
      card.style.animationDelay = `${Math.min(i * 18, 300)}ms`;

      const salary = formatSalary(job);
      const description = job.description ? job.description.substring(0, 200) : "";
      const fullDescription = job.description || "";
      const showToggle = fullDescription.length > 200;

      card.innerHTML = `
        <div class="job-card-header">
          <div>
            <h3 class="job-title">
              <a href="${job.url}" target="_blank" rel="noopener" class="job-title-link">${job.title}</a>
            </h3>
            <div class="job-company">${job.company}</div>
          </div>
          ${salary ? `<div class="job-salary">${salary}</div>` : ""}
        </div>
        <div class="job-meta">
          <span class="job-meta-item">🗓️ ${new Date(job.first_seen_at).toLocaleDateString("en-GB", { day: "2-digit", month: "short" })}</span>
          ${job.remote_scope ? `<span class="job-meta-item">📍 ${job.remote_scope}</span>` : ""}
          ${job.source_department ? `<span class="job-meta-item">📦 ${job.source_department}</span>` : ""}
        </div>
        <p class="job-description" data-short="${description}" data-full="${fullDescription}">${description}${showToggle ? "..." : ""}</p>
        ${showToggle ? `<button class="job-description-toggle">Show more</button>` : ""}
      `;
      fragment.appendChild(card);
    });
    jobsList.appendChild(fragment);
  }

  function renderDepartments(departments) {
    if (!departmentFiltersEl) return;
    departments.sort((a, b) => b.count - a.count);
    departmentFiltersEl.innerHTML = departments.map(d =>
      `<button data-dept="${d.name}">${d.name} (${d.count})</button>`
    ).join("");
  }


  // ── Event Listeners ─────────────────────────────────────────
  function setupEventListeners() {
    searchEl?.addEventListener("input", e => {
      activeFilters.search = e.target.value.trim();
      renderJobs();
    });

    departmentFiltersEl?.addEventListener("click", e => {
      if (e.target.tagName === "BUTTON") {
        const dept = e.target.dataset.dept;
        if (activeFilters.departments.has(dept)) {
          activeFilters.departments.delete(dept);
          e.target.classList.remove("active");
        } else {
          activeFilters.departments.add(dept);
          e.target.classList.add("active");
        }
        renderJobs();
      }
    });

    salaryMinEl?.addEventListener("input", e => {
      activeFilters.salaryMin = e.target.value ? parseInt(e.target.value, 10) : null;
      renderJobs();
    });
    salaryMaxEl?.addEventListener("input", e => {
      activeFilters.salaryMax = e.target.value ? parseInt(e.target.value, 10) : null;
      renderJobs();
    });

    resetFiltersEl?.addEventListener("click", () => {
      activeFilters = { search: "", departments: new Set(), salaryMin: null, salaryMax: null };
      searchEl.value = "";
      salaryMinEl.value = "";
      salaryMaxEl.value = "";
      departmentFiltersEl?.querySelectorAll("button").forEach(b => b.classList.remove("active"));
      renderJobs();
    });

    jobsList?.addEventListener('click', e => {
      if (e.target.classList.contains('job-description-toggle')) {
        const btn = e.target;
        const p = btn.previousElementSibling;
        const isShowingMore = btn.textContent === 'Show less';
        if (isShowingMore) {
          p.textContent = p.dataset.short + '...';
          btn.textContent = 'Show more';
        } else {
          p.textContent = p.dataset.full;
          btn.textContent = 'Show less';
        }
      }
    });
  }

  // ── Fetch ───────────────────────────────────────────────────
  fetch(FEED_URL)
    .then((r) => {
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return r.json();
    })
    .then((data) => {
      if (!data.jobs || data.jobs.length === 0) {
        jobsList.innerHTML = `<div class="placeholder-row">No jobs available at the moment.</div>`;
        metaEl.textContent = "Feed empty.";
        return;
      }

      allJobs = data.jobs;
      renderJobs();
      renderDepartments(data.meta.departments || []);
      setupEventListeners();

      const generated = new Date(data.meta.generated_at);
      metaEl.innerHTML =
        `Updated<br>${generated.toLocaleString("en-GB", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" })}<br><br>${data.meta.count} jobs`;
    })
    .catch(() => {
      jobsList.innerHTML = `<div class="placeholder-row">Feed temporarily unavailable.</div>`;
      metaEl.textContent = "Feed unavailable.";
    });
})();