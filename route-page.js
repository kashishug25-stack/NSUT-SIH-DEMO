const params = new URLSearchParams(location.search);
const origin = params.get("origin");
const destination = params.get("destination");
const collectionDate = params.get("collection_date");
const initialDays = Number(params.get("advance_days"));
let selectedSeries = "airline";
let routeData;
let horizonData;
let currentDays = initialDays;

function money(value) { return value == null ? "-" : `₹${Math.round(value).toLocaleString("en-IN")}`; }
function travelDate(days) {
  const [year, month, day] = collectionDate.split("-").map(Number);
  const date = new Date(year, month - 1, day + Number(days));
  return [date.getFullYear(), String(date.getMonth() + 1).padStart(2, "0"), String(date.getDate()).padStart(2, "0")].join("-");
}
function list(items) {
  return Object.entries(items || {}).map(([name, item]) => `<div class="detail-row"><span>${name}</span><strong>${money(item.median_fare)}</strong></div>`).join("") || `<div class="detail-row"><span>No stored values</span><strong>-</strong></div>`;
}
document.getElementById("exportRouteQuotesCsv").addEventListener("click", () => {
  const departureDate = travelDate(currentDays);
  const url = `/api/export/all-flights.csv?origin=${origin}&destination=${destination}&advance_days=${currentDays}&departure_date=${departureDate}`;
  window.location.href = url;
});

function load(days) {
  currentDays = days;
  const departureDate = travelDate(days);
  Promise.all([
    fetch(`/api/route?origin=${origin}&destination=${destination}&advance_days=${days}&departure_date=${departureDate}`).then((r) => r.json().then((data) => ({ ok: r.ok, data }))),
    fetch(`/api/route-horizons?origin=${origin}&destination=${destination}`).then((r) => r.json()),
    fetch(`/api/index?advance_days=${days}`).then((r) => r.json()),
  ]).then(([route, horizons, index]) => {
    if (!route.ok || !route.data.quote_count) throw new Error(`No stored quotes for ${origin}-${destination}, T+${days}, travel ${departureDate}.`);
    routeData = route.data;
    horizonData = horizons;
    document.getElementById("routeTitle").textContent = `${origin}-${destination} route intelligence`;
    document.getElementById("routeMeta").textContent = `Economy · T+${days} · live database values`;
    document.getElementById("routeContext").innerHTML = `<span><b>Collection date</b> ${collectionDate}</span><span><b>Departure date</b> ${departureDate}</span><span><b>Horizon</b> T+${days}</span><span><b>Cabin</b> Economy</span>`;
    document.getElementById("weightInfo").innerHTML = `
      <div class="detail-row"><span>Weighting method</span><strong>${route.data.weight_status || "Traffic-based route weights from DGCA route basket"}</strong></div>
      <div class="detail-row"><span>Route weight</span><strong>${((route.data.route_weight || 0) * 100).toFixed(2)}%</strong></div>
      <div class="detail-row"><span>Basket reference</span><strong>2025-01 to 2026-05</strong></div>
    `;
    document.getElementById("medianFare").textContent = money(route.data.median_fare);
    document.getElementById("lowestFare").textContent = money(route.data.minimum_fare);
    document.getElementById("quoteCount").textContent = route.data.quote_count;
    document.getElementById("indexValue").textContent = index.index_value == null ? "-" : Number(index.index_value).toFixed(2);
    document.getElementById("airlines").innerHTML = list(route.data.airlines);
    document.getElementById("sources").innerHTML = list(route.data.sources);
    document.getElementById("flights").innerHTML = route.data.quotes.slice(0, 20).map((q) => `<tr><td>${q.airline || "Unknown"}</td><td>${q.flight_number || "-"}</td><td>${q.departure_time || "-"}</td><td>${q.arrival_time || "-"}</td><td>${q.source}</td><td>${money(q.total_fare)}</td></tr>`).join("");
    document.getElementById("routeHorizons").innerHTML = `<button data-days="all">All horizons</button>${[1, 7, 15, 30, 45].map((value) => `<button class="${value === days ? "active" : ""}" data-days="${value}">T+${value}</button>`).join("")}`;
    document.querySelectorAll("#routeHorizons button[data-days]:not([data-days=\"all\"])" ).forEach((button) => button.addEventListener("click", () => load(Number(button.dataset.days))));
    document.querySelector('#routeHorizons button[data-days="all"]').addEventListener("click", () => {
      document.querySelectorAll("#routeHorizons button").forEach((item) => item.classList.remove("active"));
      document.querySelector('#routeHorizons button[data-days="all"]').classList.add("active");
      renderChart(horizonData.series[selectedSeries]);
    });
    renderChart(horizonData.series[selectedSeries]);
  }).catch((error) => { document.getElementById("routeTitle").textContent = "Route data unavailable"; document.getElementById("routeMeta").textContent = error.message; });
}
function renderChart(series) {
  const active = (series || []).filter((item) => item.points.length);
  const days = ["T+1", "T+7", "T+15", "T+30", "T+45"];
  const values = active.flatMap((item) => item.points.map((p) => p.median_fare));
  const max = Math.max(...values, 1), left = 65, top = 25, width = 960, height = 260;
  const x = (i) => left + i * (width / 4), y = (v) => top + height - (v / max) * height;
  const colors = ["#f17844", "#f2b23e", "#c96d58", "#e08b3e", "#6d8570"];
  const grid = [0, .25, .5, .75, 1].map((r) => `<line x1="${left}" y1="${y(max*r)}" x2="${left+width}" y2="${y(max*r)}" class="chart-grid" /><text x="${left-10}" y="${y(max*r)+4}" class="chart-label" text-anchor="end">${money(max*r)}</text>`).join("");
  const lines = active.map((item, index) => { const points = item.points.map((p) => [days.indexOf(p.observed_day), p.median_fare]).filter((p) => p[0] >= 0); const path = points.map((p, i) => `${i ? "L" : "M"}${x(p[0])},${y(p[1])}`).join(" "); return `<path d="${path}" class="chart-line" style="stroke:${colors[index%colors.length]}" />${points.map((p) => `<circle cx="${x(p[0])}" cy="${y(p[1])}" r="5" class="chart-dot" fill="${colors[index%colors.length]}" />`).join("")}`; }).join("");
  document.getElementById("routeChart").innerHTML = `${grid}${lines}${days.map((d,i) => `<text x="${x(i)}" y="${top+height+28}" class="chart-label" text-anchor="middle">${d}</text>`).join("")}`;
  document.getElementById("legend").innerHTML = (series || []).map((item, i) => `<span class="${item.points.length ? "" : "legend-muted"}"><i style="background:${colors[i%colors.length]}"></i>${item.name}${item.points.length ? "" : " · no data"}</span>`).join("");
}
document.querySelectorAll(".chart-tab").forEach((button) => button.addEventListener("click", () => { document.querySelectorAll(".chart-tab").forEach((b) => b.classList.remove("active")); button.classList.add("active"); selectedSeries = button.dataset.series; renderChart(horizonData.series[selectedSeries]); }));
load(initialDays);
