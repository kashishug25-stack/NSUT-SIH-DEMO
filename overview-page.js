document.getElementById("exportMarketCsv").addEventListener("click", () => {
  window.location.href = "/api/export/market-overview.csv";
});

fetch("/api/market-overview").then((response) => response.json().then((data) => ({ response, data }))).then(({ response, data }) => {
  if (!response.ok) throw new Error("Market overview unavailable.");
  const money = (value) => value == null ? "-" : `₹${Math.round(value).toLocaleString("en-IN")}`;
  document.getElementById("stats").innerHTML = `
    <div><span>Tracked routes</span><strong>${data.route_count}</strong></div>
    <div><span>Total observations</span><strong>${data.quote_count.toLocaleString("en-IN")}</strong></div>
    <div><span>Cheapest route</span><strong>${data.cheapest_route?.route || "-"} · ${money(data.cheapest_route?.median_fare)}</strong></div>
    <div><span>Highest route</span><strong>${data.highest_route?.route || "-"} · ${money(data.highest_route?.median_fare)}</strong></div>
  `;
  document.getElementById("basketWeights").innerHTML = `
    <div class="basket-meta">
      <span class="basket-badge">${data.weight_status}</span>
      <span class="basket-period">Reference period: ${data.basket_reference_period || "2025-01 to 2026-05"}</span>
    </div>
    <div class="basket-header-row">
      <span class="basket-header-label">All routes and weights</span>
    </div>
    <div class="weight-grid">
      ${data.route_weights.map((item) => `
        <div class="weight-button" aria-label="${item.route} weight ${(item.weight_percent || 0).toFixed(2)} percent">
          <span class="route-tag">${item.route}</span>
          <strong>${(item.weight_percent || 0).toFixed(2)}%</strong>
        </div>
      `).join("")}
    </div>
  `;
  document.getElementById("routes").innerHTML = data.routes.map((row) => `<tr><td>${row.route}</td>${[1,7,15,30,45].map((day) => `<td>${money(row.horizons[String(day)])}</td>`).join("")}<td>${row.quote_count}</td></tr>`).join("");
}).catch((error) => { document.getElementById("routes").innerHTML = `<tr><td colspan="7">${error.message}</td></tr>`; });
