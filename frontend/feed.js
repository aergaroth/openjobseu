(() => {
  const API_BASE = "https://openjobseu-669791171061.europe-north1.run.app";
  const FEED_URL = "/feed.json";

  const metaEl   = document.getElementById("meta");
  const jobsBody = document.getElementById("jobs-body");
  const searchEl = document.getElementById("search");

  if (!metaEl || !jobsBody) return;

  let allJobs = [];

  // ── Render ──────────────────────────────────────────────────
  function renderJobs(jobs) {
    jobsBody.innerHTML = "";

    if (jobs.length === 0) {
      jobsBody.innerHTML = `
        <tr class="placeholder-row">
          <td colspan="3">No jobs match your filter.</td>
        </tr>`;
      return;
    }

    const fragment = document.createDocumentFragment();
    jobs.forEach((job, i) => {
      const tr = document.createElement("tr");
      tr.classList.add("loaded");
      tr.style.animationDelay = `${Math.min(i * 18, 300)}ms`;
      tr.innerHTML = `
        <td><a href="${job.url}" target="_blank" rel="noopener">${job.title}</a></td>
        <td>${job.company}</td>
        <td>${new Date(job.first_seen_at).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" })}</td>
      `;
      fragment.appendChild(tr);
    });
    jobsBody.appendChild(fragment);
  }

  // ── Filter ──────────────────────────────────────────────────
  function filterJobs(query) {
    if (!query) return renderJobs(allJobs);
    const q = query.toLowerCase();
    renderJobs(allJobs.filter(j =>
      j.title.toLowerCase().includes(q) ||
      j.company.toLowerCase().includes(q)
    ));
  }

  if (searchEl) {
    searchEl.addEventListener("input", (e) => filterJobs(e.target.value.trim()));
  }

  // ── Fetch ───────────────────────────────────────────────────
  fetch(FEED_URL)
    .then((r) => {
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return r.json();
    })
    .then((data) => {
      if (!data.jobs || data.jobs.length === 0) {
        jobsBody.innerHTML = `
          <tr class="placeholder-row">
            <td colspan="3">No jobs available at the moment.</td>
          </tr>`;
        metaEl.textContent = "Feed empty.";
        return;
      }

      allJobs = data.jobs;
      renderJobs(allJobs);

      const generated = new Date(data.meta.generated_at);
      metaEl.innerHTML =
        `Updated<br>${generated.toLocaleString("en-GB", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" })}<br><br>${data.meta.count} jobs`;
    })
    .catch(() => {
      jobsBody.innerHTML = `
        <tr class="placeholder-row">
          <td colspan="3">Feed temporarily unavailable.</td>
        </tr>`;
      metaEl.textContent = "Feed unavailable.";
    });
})();
