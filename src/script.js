(function () {
  const video = document.querySelector(".sky-video");
  const poster = document.querySelector(".sky-poster");
  if (!video) return;

  video.addEventListener("error", () => {
    console.error(
      "UDAANKOSH: hero background video failed to load — check that the 'assets' folder sits next to index.html and contains hero-bg.mp4."
    );
    video.style.display = "none";
    poster.style.display = "block";
  });

  // If it hasn't started playing shortly after load, fall back too.
  window.addEventListener("load", () => {
    setTimeout(() => {
      if (video.readyState === 0) {
        video.style.display = "none";
        poster.style.display = "block";
      }
    }, 2500);
  });
})();

const CITIES = [
  ["DEL", "Delhi"], ["BOM", "Mumbai"], ["BLR", "Bengaluru"],
  ["CCU", "Kolkata"], ["HYD", "Hyderabad"], ["GOI", "Goa"],
  ["PAT", "Patna"], ["MAA", "Chennai"],
];
const ROUTES = new Set([
  "DEL-BOM", "DEL-BLR", "DEL-CCU", "DEL-HYD", "DEL-GOI", "DEL-PAT",
  "BOM-BLR", "MAA-DEL",
]);

const originSelect = document.getElementById("origin");
const destinationSelect = document.getElementById("destination");
let latestObservationDate = null;

 CITIES.forEach(([code, name], i) => {
  const o1 = document.createElement("option");
  o1.value = code;
  o1.textContent = `${name} (${code})`;
  originSelect.appendChild(o1);

  const o2 = document.createElement("option");
  o2.value = code;
  o2.textContent = `${name} (${code})`;
  destinationSelect.appendChild(o2);
});

fetch("/api/meta?ts=" + Date.now(), {cache:"no-store"})
  .then((response) => response.json())
  .then((data) => {
    latestObservationDate = data.latest_observation_date;
    updateDateHint();
  })
  .catch(() => {});

fetch("/api/market-overview?ts=" + Date.now(), {cache:"no-store"})
  .then((response) => response.json())
  .then((data) => {
    document.getElementById("homeQuotes").textContent = Number(data.quote_count).toLocaleString("en-IN");
    document.getElementById("homeRoutes").textContent = data.route_count;
    document.getElementById("homeSources").textContent = "3";
    renderFareTerrain(data);
  })
  .catch(() => {});

function paintIndex(data) {
  const value = Number(data.index_value);
  const formatted = Number.isFinite(value) ? value.toFixed(2) : "—";
  const isBaseDay = data.status === "base_day";
  document.getElementById("homeIndex").textContent = formatted;
  document.getElementById("heroIndexValue").textContent = formatted;
  document.getElementById("heroIndexState").textContent = isBaseDay ? "BASE DAY · 100" : (value < 80 ? "VERY CHEAP" : value < 95 ? "CHEAP" : value <= 105 ? "NORMAL" : value <= 120 ? "EXPENSIVE" : "VERY EXPENSIVE");
  document.getElementById("heroIndexMessage").textContent = isBaseDay
    ? `First successful live collection (${data.base_period}) is the official base period. Base index = 100.`
    : `Compared with the ${data.base_period} baseline using DGCA traffic-weighted route medians.`;
  document.getElementById("heroIndexBase").textContent = data.base_period || "—";
  document.getElementById("heroIndexCurrent").textContent = data.current_period || "—";
  document.getElementById("heroIndexCoverage").textContent = `${data.route_count} / 8`;
}

fetch("/api/index?advance_days=1&ts=" + Date.now(), {cache:"no-store"})
  .then(async (response) => {
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Index endpoint unavailable");
    return data;
  })
  .then(paintIndex)
  .catch(async (error) => {
    // Fail-safe for a stale/partial local API: if the connected database has
    // exactly one observation day, its official base-day index is mathematically 100.
    try {
      const healthResponse = await fetch("/api/health?ts=" + Date.now(), {cache:"no-store"});
      const health = await healthResponse.json();
      if (health.database === "connected" && Number(health.observation_days) === 1 && Number(health.total_quotes) > 0) {
        paintIndex({
          index_value: 100, status: "base_day", base_period: health.latest_observed,
          current_period: health.latest_observed, route_count: 8
        });
        return;
      }
    } catch (_) {}
    document.getElementById("homeIndex").textContent = "—";
    document.getElementById("heroIndexValue").textContent = "—";
    document.getElementById("heroIndexState").textContent = "INDEX UNAVAILABLE";
    document.getElementById("heroIndexMessage").textContent = error.message || "No valid fare observations are available.";
    document.getElementById("heroIndexBase").textContent = "—";
    document.getElementById("heroIndexCurrent").textContent = "—";
    document.getElementById("heroIndexCoverage").textContent = "0 / 8";
  });


function renderFareTerrain(data) {
  const grid = document.getElementById("terrainGrid");
  if (!grid) return;
  const routes = (data.routes || []).slice().sort((a, b) => String(a.route).localeCompare(String(b.route)));
  const horizonDays = [1, 7, 15, 30, 45];
  const values = routes.flatMap(r => horizonDays.map(d => Number(r.horizons?.[String(d)] || 0))).filter(v => v > 0);
  if (!values.length) {
    grid.innerHTML = '<div class="terrain-empty">No observed fare surface is available yet.</div>';
    const labels = document.getElementById("terrainLabels");
    if (labels) labels.innerHTML = "";
    return;
  }
  const min = Math.min(...values), max = Math.max(...values);
  const range = Math.max(max - min, 1);
  grid.innerHTML = routes.flatMap(route => horizonDays.map(day => {
    const fare = Number(route.horizons?.[String(day)] || 0);
    const pct = fare ? 18 + ((fare - min) / range) * 72 : 4;
    const label = fare ? `₹${Math.round(fare).toLocaleString("en-IN")}` : "—";
    const barHeight = fare ? Math.round(18 + ((fare - min) / range) * 92) : 5;
    return `<div class="terrain-cell" title="${route.route} · T+${day} · ${label}"><span>${route.route}</span><div class="terrain-bar" style="--bar-h:${barHeight}px"><i class="terrain-face terrain-front"></i><i class="terrain-face terrain-right"></i><i class="terrain-face terrain-top"></i></div><b class="terrain-fare">${label}</b></div>`;
  })).join('');
  const labels = document.getElementById("terrainLabels");
  if (labels) labels.innerHTML = horizonDays.map(d => `<span>T+${d}</span>`).join('');
}

function updateDateHint() {
  const hint = document.getElementById("dateHint");
  const days = document.getElementById("horizon").value;
  if (!latestObservationDate || !days) {
    hint.textContent = "Select a horizon to calculate departure date from the latest collection.";
    document.getElementById("depDate").value = "";
    return;
  }
  const iso = travelDateFor(latestObservationDate, days);
  document.getElementById("depDate").value = iso;
  hint.textContent = `Latest collection: ${latestObservationDate} · T+${days} departure: ${iso}`;
}

function travelDateFor(collectionDate, days) {
  const [year, month, day] = collectionDate.split("-").map(Number);
  const travelDate = new Date(year, month - 1, day + Number(days));
  return [travelDate.getFullYear(), String(travelDate.getMonth() + 1).padStart(2, "0"), String(travelDate.getDate()).padStart(2, "0")].join("-");
}

document.getElementById("horizon").addEventListener("change", updateDateHint);

let routeSet = false;
let latestRouteData = null;
let selectedSeries = "airline";
let selectedDays = null;
let selectedView = "lead_time";
let chartFrame = null;
let chartModel = null;
let chartMotionToken = 0;
let chartPlaybackTimer = null;
const resultBox = document.getElementById("resultBox");

function showResult(html, isError) {
  resultBox.hidden = false;
  resultBox.innerHTML = html;
  resultBox.classList.toggle("error", !!isError);
}

document.getElementById("inputRouteBtn").addEventListener("click", () => {
  if (!originSelect.value || !destinationSelect.value) {
    showResult("Select a departure and arrival airport first.", true);
    return;
  }
  const route = `${originSelect.value}-${destinationSelect.value}`;
  if (!ROUTES.has(route)) {
    showResult("Choose one of the supported domestic corridors.", true);
    return;
  }
  routeSet = true;
  showResult(
    `Route locked: <strong>${route.replace("-", " → ")}</strong> · Economy`,
    false
  );
});

document.getElementById("exportRouteCsvBtn").addEventListener("click", () => {
  if (!routeSet) {
    showResult("Input the route before exporting its flight quotes.", true);
    return;
  }
  if (!document.getElementById("horizon").value) {
    showResult("Select an advance window first.", true);
    return;
  }
  const travelDate = document.getElementById("depDate").value;
  if (!travelDate) {
    showResult("Select an advance window to calculate the departure date.", true);
    return;
  }
  const origin = originSelect.value;
  const destination = destinationSelect.value;
  window.location.href = `/api/export/all-flights.csv?origin=${origin}&destination=${destination}&advance_days=${document.getElementById("horizon").value}&departure_date=${travelDate}`;
});

document.getElementById("overviewBtn").addEventListener("click", () => {
  window.location.href = "/market-overview.html";
});

document.getElementById("sourceHealthBtn").addEventListener("click", () => {
  window.location.href = "/source-health.html";
});

document.getElementById("apixBtn").addEventListener("click", () => {
  window.location.href = "/apix.html";
});

document.getElementById("cpiBtn").addEventListener("click", () => {
  window.location.href = "/cpi.html";
});

document.getElementById("forecastBtn").addEventListener("click", () => {
  window.location.href = "/prediction.html";
});

document.getElementById("overviewBack").addEventListener("click", () => {
  document.getElementById("marketOverview").hidden = true;
  document.querySelector(".cards-wrap").hidden = false;
  document.querySelector(".hero").hidden = false;
});

document.getElementById("computeFareBtn").addEventListener("click", () => {
  if (!routeSet) {
    showResult("Input the route before computing fare intelligence.", true);
    return;
  }
  if (!document.getElementById("horizon").value || !document.getElementById("cabin").value) {
    showResult("Select an advance window and cabin first.", true);
    return;
  }
  const route = `${originSelect.value}-${destinationSelect.value}`;
  const days = document.getElementById("horizon").value;
  const collectionDate = latestObservationDate;
  const travelDate = document.getElementById("depDate").value;
  if (!collectionDate || !travelDate) {
    showResult("Select an advance window to calculate the departure date.", true);
    return;
  }
  const dateQuery = `&departure_date=${travelDate}`;
  fetch(`/api/route?origin=${originSelect.value}&destination=${destinationSelect.value}&advance_days=${days}${dateQuery}`)
    .then((response) => response.json().then((data) => ({ response, data })))
    .then(({ response, data }) => {
      if (!response.ok) throw new Error(data.error || "No route data available.");
      if (!data.quote_count) {
        clearRadar();
        const expected = data.expected_departure_date
          ? ` Stored T+${days} travel data is for ${data.expected_departure_date}.`
          : "";
        throw new Error(`No quotes found for ${route}, collection ${collectionDate}, travel ${travelDate}.${expected}`);
      }
      window.location.href = `/route.html?origin=${originSelect.value}&destination=${destinationSelect.value}&collection_date=${collectionDate}&advance_days=${days}`;
    })
    .catch((error) => showResult(error.message, true));
});

/* ---------- Market Radar refresh ---------- */
function updateRadar(data) {
  if (!document.getElementById("rRoute")) return;
  const fares = data.quotes.map((quote) => quote.total_fare).filter(Boolean);
  const spread = data.median_fare ? (data.maximum_fare - data.minimum_fare) / data.median_fare : 0;
  document.getElementById("rRoute").textContent = `${data.route} · T+${data.advance_days}`;
  document.getElementById("rAvg").textContent = `₹${Math.round(data.median_fare).toLocaleString("en-IN")}`;
  document.getElementById("rCheapest").textContent = `₹${Math.round(data.minimum_fare).toLocaleString("en-IN")}`;
  document.getElementById("rVolatility").textContent = spread > 0.8 ? "High" : spread > 0.4 ? "Moderate" : "Low";
  document.getElementById("rScore").textContent = `${fares.length} quotes`;
}

function clearRadar() {
  if (!document.getElementById("rRoute")) return;
  document.getElementById("rRoute").textContent = "Awaiting query";
  document.getElementById("rAvg").textContent = "—";
  document.getElementById("rCheapest").textContent = "—";
  document.getElementById("rVolatility").textContent = "—";
  document.getElementById("rScore").textContent = "No data";
  document.getElementById("routeDetails").hidden = true;
  latestRouteData = null;
  document.body.classList.remove("route-mode");
}

function renderDetails(data) {
  latestRouteData = data;
  document.body.classList.add("route-mode");
  selectedView = data.view === "lead_time" ? "lead_time" : "observation";
  const details = document.getElementById("routeDetails");
  details.hidden = false;
  document.getElementById("detailsTitle").textContent = `${data.route} route intelligence`;
  document.getElementById("detailsMeta").textContent = `Economy · T+${data.advance_days} · ${data.departure_date} · live database values`;
  document.getElementById("detailsCount").textContent = `${data.quote_count} quotes`;
  selectedDays = data.view === "lead_time" ? "all" : String(data.advance_days);
  document.querySelectorAll("#detailHorizons button").forEach((button) => button.classList.toggle("active", button.dataset.days === selectedDays));
  document.getElementById("queryContext").innerHTML = `
    <span><b>Departure</b> ${originSelect.options[originSelect.selectedIndex].text}</span>
    <span><b>Arrival</b> ${destinationSelect.options[destinationSelect.selectedIndex].text}</span>
    <span><b>Collected</b> ${latestObservationDate}</span>
    <span><b>Travel date</b> ${data.departure_date}</span>
    <span><b>Cabin</b> Economy</span>`;

  const list = (items) => Object.entries(items).map(([name, item]) => `
    <div class="detail-row"><span>${name}</span><strong>₹${Math.round(item.median_fare).toLocaleString("en-IN")}</strong></div>
  `).join("");
  document.getElementById("sourceList").innerHTML = list(data.sources);
  document.getElementById("airlineList").innerHTML = list(data.airlines);
  document.getElementById("flightRows").innerHTML = data.quotes.slice(0, 12).map((quote) => `
    <tr><td>${quote.airline || "Unknown"}</td><td>${quote.flight_number || "—"}</td><td>${quote.departure_time || "—"}</td><td>${quote.arrival_time || "—"}</td><td>${quote.source}</td><td>₹${Math.round(quote.total_fare).toLocaleString("en-IN")}</td></tr>`).join("");
  renderLineChart(selectedSeries);
}

function loadIndex(days) {
  fetch(`/api/index?advance_days=${days}&ts=${Date.now()}`, {cache:"no-store"})
    .then((response) => response.json().then((data) => ({ response, data })))
    .then(({ response, data }) => {
      if (!response.ok) throw new Error(data.error || "Index unavailable");
      document.getElementById("indexValue").textContent = Number(data.index_value).toFixed(2);
      document.getElementById("indexBase").textContent = data.base_period;
      document.getElementById("indexCurrent").textContent = data.current_period;
      document.getElementById("indexCoverage").textContent = `${data.route_count} routes`;
    })
    .catch((error) => {
      document.getElementById("indexValue").textContent = "BUILDING";
      document.getElementById("indexBase").textContent = "—";
      document.getElementById("indexCurrent").textContent = "—";
      document.getElementById("indexCoverage").textContent = "—";
    });
}

function loadIndexSeries(days) {
  fetch(`/api/index-series?advance_days=${days}&ts=${Date.now()}`, {cache:"no-store"})
    .then((response) => response.json().then((data) => ({ response, data })))
    .then(({ response, data }) => {
      if (!response.ok) throw new Error(data.error || "Index trend unavailable");
      window.requestAnimationFrame(() => renderIndexChart(data));
    })
    .catch(() => {
      document.getElementById("indexChart").innerHTML = '<text x="450" y="95" class="chart-label" text-anchor="middle">Index trend unavailable</text>';
    });
}

function renderIndexChart(data) {
  const points = data.points || [];
  const svg = document.getElementById("indexChart");
  if (!points.length) {
    svg.innerHTML = '<text x="450" y="95" class="chart-label" text-anchor="middle">No index observations</text>';
    return;
  }
  const left = 58, top = 15, width = 800, height = 120;
  const min = Math.min(...points.map((point) => point.index_value), 100) - 2;
  const max = Math.max(...points.map((point) => point.index_value), 100) + 2;
  const x = (index) => left + (points.length === 1 ? width / 2 : index / (points.length - 1) * width);
  const y = (value) => top + height - ((value - min) / (max - min)) * height;
  const path = points.map((point, index) => `${index ? "L" : "M"}${x(index)},${y(point.index_value)}`).join(" ");
  svg.innerHTML = `<line x1="${left}" y1="${y(100)}" x2="${left + width}" y2="${y(100)}" class="index-base-line" /><path d="${path}" class="index-line" /><text x="${left - 8}" y="${y(100) + 4}" class="chart-label" text-anchor="end">100</text>${points.map((point, index) => `<circle cx="${x(index)}" cy="${y(point.index_value)}" r="4" class="index-dot" /><text x="${x(index)}" y="${top + height + 24}" class="chart-label" text-anchor="middle">${point.observed_day.slice(5)}</text>`).join("")}`;
}

function clearIndex() {
  document.getElementById("indexValue").textContent = "Select horizon";
  document.getElementById("indexBase").textContent = "—";
  document.getElementById("indexCurrent").textContent = "—";
  document.getElementById("indexCoverage").textContent = "—";
}

function renderLineChart(seriesType) {
  if (!latestRouteData) return;
  const sourceSeries = latestRouteData.series;
  const allSeries = sourceSeries[seriesType] || [];
  const series = allSeries.filter((item) => item.points.length);
  const days = selectedView === "lead_time"
    ? ["T+1", "T+7", "T+15", "T+30", "T+45"].filter((day) => series.some((item) => item.points.some((point) => (point.observed_day || point.label) === day)))
    : [...new Set(series.flatMap((item) => item.points.map((point) => point.observed_day || point.label)))].sort();
  const svg = document.getElementById("lineChart");
  const colors = ["#f17844", "#f2b23e", "#c96d58", "#e08b3e", "#6d8570"];
  const left = 68, top = 24, width = Math.max(920, days.length * 190), height = 270;
  const values = series.flatMap((item) => item.points.map((point) => point.median_fare));
  const max = Math.max(...values, 1);
  const x = (index) => left + (days.length <= 1 ? width / 2 : (index / (days.length - 1)) * width);
  const y = (value) => top + height - (value / max) * height;
  const grid = [0, 0.25, 0.5, 0.75, 1].map((ratio) => `
    <line x1="${left}" y1="${y(max * ratio)}" x2="${left + width}" y2="${y(max * ratio)}" class="chart-grid" />
    <text x="${left - 12}" y="${y(max * ratio) + 4}" class="chart-label" text-anchor="end">₹${Math.round(max * ratio).toLocaleString("en-IN")}</text>`).join("");
  const labels = days.map((day, index) => `<text x="${x(index)}" y="${top + height + 28}" class="chart-label" text-anchor="middle">${selectedView === "lead_time" ? day : day.slice(5)}</text>`).join("");
  const scene = `<defs><linearGradient id="areaWarm" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#f17844" stop-opacity=".28"/><stop offset="1" stop-color="#f17844" stop-opacity="0"/></linearGradient><linearGradient id="areaGold" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#f2b23e" stop-opacity=".24"/><stop offset="1" stop-color="#f2b23e" stop-opacity="0"/></linearGradient></defs>${grid}<g id="chartSeries"></g>${labels}<line id="hoverLine" class="hover-line" y1="${top}" y2="${top + height}" /><line id="playhead" class="playhead" y1="${top}" y2="${top + height}" /><g id="chartTooltip" class="chart-tooltip" visibility="hidden"><rect width="170" height="42" rx="8"></rect><text id="tooltipDate" x="10" y="16"></text><text id="tooltipValue" x="10" y="32"></text></g><rect class="chart-hit" x="${left}" y="${top}" width="${width}" height="${height}" />`;
  svg.setAttribute("viewBox", `0 0 ${left + width + 40} 360`);
  svg.innerHTML = scene;
  chartModel = { series, allSeries, days, colors, left, top, width, height, x, y, max };
  animateChart();
  window.setTimeout(playChartMotion, 1500);
  document.getElementById("chartLegend").innerHTML = allSeries.map((item, index) => `<span class="${item.points.length ? "" : "legend-muted"}"><i style="background:${colors[index % colors.length]}"></i>${item.name}${item.points.length ? "" : " · no data"}</span>`).join("");
  document.getElementById("chartAxisNote").textContent = selectedView === "lead_time"
    ? "X-axis: advance-booking horizon · Y-axis: median total fare in INR · observed database values"
    : "X-axis: observation date · Y-axis: median total fare in INR · selected-horizon database values";

  svg.querySelector(".chart-hit").addEventListener("pointermove", (event) => updateChartHover(event, svg));
  svg.querySelector(".chart-hit").addEventListener("pointerleave", () => {
    svg.querySelector("#hoverLine").style.visibility = "hidden";
    svg.querySelector("#chartTooltip").setAttribute("visibility", "hidden");
  });
}

function smoothPath(points) {
  if (!points.length) return "";
  if (points.length === 1) return `M${points[0][0]},${points[0][1]}`;
  let path = `M${points[0][0]},${points[0][1]}`;
  for (let i = 0; i < points.length - 1; i += 1) {
    const current = points[i];
    const next = points[i + 1];
    const midpoint = (current[0] + next[0]) / 2;
    path += ` C${midpoint},${current[1]} ${midpoint},${next[1]} ${next[0]},${next[1]}`;
  }
  return path;
}

function animateChart() {
  if (!chartModel) return;
  const token = ++chartMotionToken;
  if (chartFrame) cancelAnimationFrame(chartFrame);
  const started = performance.now();
  const duration = 1400;
  const draw = (now) => {
    if (token !== chartMotionToken) return;
    const progress = Math.min(1, (now - started) / duration);
    const eased = 1 - Math.pow(1 - progress, 3);
    const group = document.getElementById("chartSeries");
    if (!group) return;
    group.innerHTML = chartModel.series.map((item, index) => {
      const points = item.points.slice().sort((a, b) => (a.observed_day || a.label).localeCompare(b.observed_day || b.label));
      const curvePoints = points.map((point) => {
        const targetY = chartModel.y(point.median_fare);
        const startY = chartModel.top + chartModel.height;
        return [chartModel.x(chartModel.days.indexOf(point.observed_day || point.label)), startY + (targetY - startY) * eased];
      });
      const path = smoothPath(curvePoints);
      const areaPath = curvePoints.length > 1
        ? `${path} L${curvePoints[curvePoints.length - 1][0]},${chartModel.top + chartModel.height} L${curvePoints[0][0]},${chartModel.top + chartModel.height} Z`
        : "";
      const dots = points.map((point) => {
        const targetY = chartModel.y(point.median_fare);
        const startY = chartModel.top + chartModel.height;
        return `<circle cx="${chartModel.x(chartModel.days.indexOf(point.observed_day || point.label))}" cy="${startY + (targetY - startY) * eased}" r="5" fill="${chartModel.colors[index % chartModel.colors.length]}" class="chart-dot" data-series="${item.name}" data-value="${point.median_fare}" data-day="${point.observed_day || point.label}" />`;
      }).join("");
      const areaId = index % 2 === 0 ? "areaWarm" : "areaGold";
      const stroke = chartModel.colors[index % chartModel.colors.length];
      const depth = 7;
      const depthPath = curvePoints.length ? curvePoints.map((p, i) => `${i ? "L" : "M"}${p[0] + depth},${p[1] + depth}`).join(" ") : "";
      return `${areaPath ? `<path d="${areaPath}" class="chart-area" fill="url(#${areaId})" />` : ""}${depthPath ? `<path d="${depthPath}" class="chart-line-depth" style="stroke:${stroke}" />` : ""}<path d="${path}" class="chart-line" style="stroke:${stroke}" />${dots}`;
    }).join("");
    if (progress < 1) chartFrame = requestAnimationFrame(draw);
  };
  chartFrame = requestAnimationFrame(draw);
}

function playChartMotion() {
  if (!chartModel || chartModel.days.length < 2) {
    animateChart();
    return;
  }
  if (chartPlaybackTimer) clearInterval(chartPlaybackTimer);
  let index = 0;
  const focus = () => {
    const svg = document.getElementById("lineChart");
    const day = chartModel.days[index];
    const points = chartModel.series.flatMap((item) => item.points.filter((point) => (point.observed_day || point.label) === day).map((point) => ({ ...point, name: item.name })));
    const marker = svg.querySelector("#playhead");
    if (marker) {
      marker.setAttribute("x1", chartModel.x(index));
      marker.setAttribute("x2", chartModel.x(index));
      marker.style.visibility = "visible";
    }
    const best = points.sort((a, b) => b.median_fare - a.median_fare)[0];
    if (best) {
      const tooltip = svg.querySelector("#chartTooltip");
      tooltip.setAttribute("transform", `translate(${Math.min(chartModel.x(index) + 10, 710)},${chartModel.top + 10})`);
      svg.querySelector("#tooltipDate").textContent = day;
      svg.querySelector("#tooltipValue").textContent = `${best.name}: ₹${Math.round(best.median_fare).toLocaleString("en-IN")}`;
      tooltip.setAttribute("visibility", "visible");
    }
    index = (index + 1) % chartModel.days.length;
  };
  focus();
  chartPlaybackTimer = setInterval(focus, 1100);
}

function updateChartHover(event, svg) {
  if (!chartModel || !chartModel.days.length) return;
  const rect = svg.getBoundingClientRect();
  const svgX = ((event.clientX - rect.left) / rect.width) * 900;
  const nearest = Math.max(0, Math.min(chartModel.days.length - 1, Math.round((svgX - chartModel.left) / chartModel.width * (chartModel.days.length - 1))));
  const day = chartModel.days[nearest];
  const points = chartModel.series.flatMap((item) => item.points.filter((point) => (point.observed_day || point.label) === day).map((point) => ({ ...point, name: item.name })));
  const best = points.sort((a, b) => b.median_fare - a.median_fare)[0];
  const hoverLine = svg.querySelector("#hoverLine");
  const tooltip = svg.querySelector("#chartTooltip");
  hoverLine.setAttribute("x1", chartModel.x(nearest));
  hoverLine.setAttribute("x2", chartModel.x(nearest));
  hoverLine.style.visibility = "visible";
  tooltip.setAttribute("transform", `translate(${Math.min(chartModel.x(nearest) + 10, 710)},${chartModel.top + 10})`);
  svg.querySelector("#tooltipDate").textContent = day;
  svg.querySelector("#tooltipValue").textContent = best ? `${best.name}: ₹${Math.round(best.median_fare).toLocaleString("en-IN")}` : "No observed fare";
  tooltip.setAttribute("visibility", "visible");
}

document.querySelectorAll(".chart-tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    if (tab.dataset.view) {
      selectedView = tab.dataset.view;
      document.querySelectorAll(".chart-tab[data-view]").forEach((button) => button.classList.toggle("active", button === tab));
    }
    if (tab.dataset.series) {
      selectedSeries = tab.dataset.series;
      document.querySelectorAll(".chart-tab[data-series]").forEach((button) => button.classList.toggle("active", button === tab));
    }
    renderLineChart(selectedSeries);
  });
});

document.getElementById("replayChart").addEventListener("click", () => {
  animateChart();
  playChartMotion();
});

document.querySelectorAll("#detailHorizons button").forEach((button) => {
  button.addEventListener("click", () => {
    if (!latestRouteData || button.dataset.days === selectedDays) return;
    const days = button.dataset.days;
    const collectionDate = latestObservationDate;
    if (days === "all") {
      fetch(`/api/route-horizons?origin=${originSelect.value}&destination=${destinationSelect.value}`)
        .then((response) => response.json().then((data) => ({ response, data })))
        .then(({ response, data }) => {
          if (!response.ok || !data.quote_count) throw new Error("No stored horizon data for this route.");
          latestRouteData = data;
          selectedDays = "all";
          clearIndex();
          renderDetails({ ...data, departure_date: "All stored travel dates", advance_days: "all", quotes: [] });
        })
        .catch((error) => showResult(error.message, true));
      return;
    }
    const travelDate = travelDateFor(collectionDate, days);
    document.getElementById("depDate").value = travelDate;
    fetch(`/api/route?origin=${originSelect.value}&destination=${destinationSelect.value}&advance_days=${days}&departure_date=${travelDate}`)
      .then((response) => response.json().then((data) => ({ response, data })))
      .then(({ response, data }) => {
        if (!response.ok || !data.quote_count) throw new Error(`No stored quotes for T+${days} from collection date ${collectionDate} (travel ${travelDate}).`);
        updateRadar(data);
        renderDetails(data);
        loadIndex(days);
        loadIndexSeries(days);
      })
      .catch((error) => showResult(error.message, true));
  });
});

document.getElementById("backToQuery").addEventListener("click", () => {
  document.body.classList.remove("route-mode");
  document.getElementById("routeDetails").hidden = true;
  window.scrollTo({ top: 0, behavior: "smooth" });
});

const refreshButton = document.getElementById("refreshBtn");
if (refreshButton) {
  refreshButton.addEventListener("click", () => {
    document.getElementById("computeFareBtn").click();
  });
}

/* ---------- Smooth scroll for nav links ---------- */
document.querySelectorAll('a[href^="#"]').forEach((link) => {
  link.addEventListener("click", (e) => {
    e.preventDefault();
    const target = document.querySelector(link.getAttribute("href"));
    if (target) target.scrollIntoView({ behavior: "smooth" });
  });
});


