(() => {
  const API_BASE = "https://openjobseu-669791171061.europe-north1.run.app";
  const FEED_URL = "/feed.json";

  const metaEl = document.getElementById("meta");
  const jobsBody = document.querySelector("#jobs-table tbody");

  if (!metaEl || !jobsBody) {
    return;
  }

  metaEl.textContent = "Loading feed...";

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
})();
