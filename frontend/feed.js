(() => {
  const API_BASE = "https://openjobseu-669791171061.europe-north1.run.app";
  const FEED_URL = "/feed.json";
  const STATS_URL = `${API_BASE}/jobs/stats/compliance-7d`;

  const metaEl = document.getElementById("meta");
  const jobsBody = document.querySelector("#jobs-table tbody");
  const statsMetaEl = document.getElementById("stats-meta");
  const statsBody = document.querySelector("#stats-table tbody");

  if (!metaEl || !jobsBody || !statsMetaEl || !statsBody) {
    return;
  }

  metaEl.textContent = "Loading feed...";
  statsMetaEl.textContent = "Loading stats...";

  fetch(FEED_URL)
    .then((r) => r.json())
    .then((data) => {
      jobsBody.innerHTML = "";

      if (!data.jobs || data.jobs.length === 0) {
        metaEl.textContent = "No jobs available at the moment.";
        return;
      }

      data.jobs.forEach((job) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td><a href="${job.url}" target="_blank" rel="noopener">${job.title}</a></td>
          <td>${job.company}</td>
          <td>${job.source}</td>
          <td>${new Date(job.first_seen_at).toLocaleDateString()}</td>
        `;
        jobsBody.appendChild(tr);
      });

      metaEl.textContent =
        `Updated ${new Date(data.meta.generated_at).toLocaleString()} · ${data.meta.count} jobs`;
    })
    .catch(() => {
      metaEl.textContent = "Job feed is temporarily unavailable.";
    });

  fetch(STATS_URL)
    .then((r) => r.json())
    .then((data) => {
      statsBody.innerHTML = "";
      const ratio =
        data.approved_ratio_pct === null
          ? "N/A"
          : `${Number(data.approved_ratio_pct).toFixed(2)}%`;

      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${data.total_jobs}</td>
        <td>${data.approved}</td>
        <td>${data.review}</td>
        <td>${data.rejected}</td>
        <td>${ratio}</td>
      `;
      statsBody.appendChild(tr);

      statsMetaEl.textContent = "Window: last 7 days by first_seen_at.";
    })
    .catch(() => {
      statsMetaEl.textContent = "Stats are temporarily unavailable.";
    });
})();
