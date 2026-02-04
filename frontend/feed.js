(() => {
  const FEED_URL =
    "https://openjobseu-anobnjle6q-lz.a.run.app/jobs/feed";

  const metaEl = document.getElementById("meta");
  const tbody = document.querySelector("#jobs-table tbody");

  if (!metaEl || !tbody) {
    return;
  }

  metaEl.textContent = "Loading feed";

fetch(FEED_URL)
  .then(r => r.json())
  .then(data => {
    const tbody = document.querySelector("#jobs-table tbody");
    const meta = document.getElementById("meta");

    tbody.innerHTML = "";

    if (!data.jobs || data.jobs.length === 0) {
      meta.textContent = "No jobs available at the moment.";
      return;
    }

    data.jobs.forEach(job => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><a href="${job.url}" target="_blank" rel="noopener">${job.title}</a></td>
        <td>${job.company}</td>
        <td>${job.source}</td>
        <td>${new Date(job.first_seen_at).toLocaleDateString()}</td>
      `;
      tbody.appendChild(tr);
    });

    meta.textContent =
      `Updated ${new Date(data.meta.generated_at).toLocaleString()} · ${data.meta.count} jobs`;
  })
  .catch(() => {
    document.getElementById("meta").textContent =
      "Job feed is temporarily unavailable.";
  });

})();







