document.getElementById("exportAllFlightsCsv").addEventListener("click", () => {
  window.location.href = "/api/export/all-flights.csv";
});

document.getElementById("exportSourceHealthCsv").addEventListener("click", () => {
  window.location.href = "/api/export/source-health.csv";
});

fetch("/api/source-health")
  .then((response) => response.json().then((data) => ({ response, data })))
  .then(({ response, data }) => {
    if (!response.ok) throw new Error("Source health unavailable.");
    const summary = data.cleaning_summary || {};
    document.getElementById("healthMeta").textContent = `Latest stored observation: ${data.latest_observed || "-"}`;
    document.getElementById("healthStats").innerHTML = `
      <div><span>Total raw quotes</span><strong>${Number(data.total_quotes).toLocaleString("en-IN")}</strong></div>
      <div><span>Sources tracked</span><strong>${data.sources.length}</strong></div>
      <div><span>Route-horizon coverage cells</span><strong>${data.coverage.length}</strong></div>
      <div><span>Database mode</span><strong>Read-only</strong></div>`;
    document.getElementById("cleaningSummaryRows").innerHTML = `
      <tr><td>Duplicate quote rows</td><td>${summary.duplicate_rows ?? 0}</td></tr>
      <tr><td>Invalid or unusable quotes</td><td>${summary.invalid_quotes ?? 0}</td></tr>
      <tr><td>Rows flagged as outliers</td><td>${summary.outlier_rows ?? 0}</td></tr>
      <tr><td>Route groups containing outliers</td><td>${summary.route_groups_with_outliers ?? 0}</td></tr>`;
    document.getElementById("sourceRows").innerHTML = data.sources.length
      ? data.sources.map((source) => `
        <tr><td>${source.source}</td><td>${source.quote_count}</td><td>${source.route_count}</td><td>${source.horizon_count}</td><td>${source.latest_observed || "-"}</td><td>${source.missing_base_fare} / ${source.missing_taxes}</td></tr>`).join("")
      : '<tr><td colspan="6">No source coverage rows available.</td></tr>';
    document.getElementById("coverageRows").innerHTML = data.coverage.length
      ? data.coverage.map((item) => `<tr><td>${item.route}</td><td>T+${item.advance_days}</td><td>${item.quote_count}</td></tr>`).join("")
      : '<tr><td colspan="3">No route-horizon coverage rows available.</td></tr>';
  })
  .catch((error) => { document.getElementById("healthMeta").textContent = error.message; });
