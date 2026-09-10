const defaultDays = 7;
let activeDays = defaultDays;
let selectedRoute = "all";

const exportBtn = document.getElementById("exportForecastCsv");
const forecastHorizons = document.getElementById("forecastHorizons");
const forecastRouteSelect = document.getElementById("forecastRouteSelect");

function setForecastDays(days) {
  activeDays = days;
  const buttons = forecastHorizons ? forecastHorizons.querySelectorAll("button") : [];
  buttons.forEach((button) => {
    button.classList.toggle("active", button.dataset.days === String(days));
  });
  if (exportBtn) {
    exportBtn.onclick = () => {
      window.location.href = `/api/export/model-forecast.csv?advance_days=${days}`;
    };
  }
  loadForecast(days);
}

function money(value) {
  return value == null ? "-" : `₹${Math.round(value).toLocaleString("en-IN")}`;
}

function renderForecastChart(rows) {
  const svg = document.getElementById("forecastChart");
  const legend = document.getElementById("forecastLegend");
  if (!svg) return;

  const orderedRows = [...rows].sort((a, b) => Number(b.forecast) - Number(a.forecast));
  const maxValue = Math.max(...orderedRows.map((row) => Number(row.forecast) || 0), 1);
  const left = 160;
  const chartWidth = 650;
  const barHeight = 18;
  const barGap = 18;
  const totalHeight = Math.max(180, orderedRows.length * (barHeight + barGap) + 50);

  svg.setAttribute("viewBox", `0 0 960 ${totalHeight}`);

  const grid = [0, 0.25, 0.5, 0.75, 1].map((ratio) => {
    const x = left + chartWidth * ratio;
    return `<line x1="${x}" y1="20" x2="${x}" y2="${totalHeight - 30}" class="forecast-grid" />`;
  }).join("");

  const bars = orderedRows.map((row, index) => {
    const y = 28 + index * (barHeight + barGap);
    const width = Math.max(8, (Number(row.forecast) / maxValue) * chartWidth);

    return `
      <g class="forecast-bar-group">
        <text x="12" y="${y + 14}" class="forecast-label">${row.route}</text>
        <rect class="forecast-bar" x="${left}" y="${y}" width="${width}" height="${barHeight}" rx="8" />
        <text x="${left + width + 12}" y="${y + 14}" class="forecast-value">${money(row.forecast)}</text>
        <title>${row.route}: ${money(row.forecast)} | ${row.horizon} | latest observed ${row.observed}</title>
      </g>
    `;
  }).join("");

  svg.innerHTML = `
    ${grid}
    <line x1="${left}" y1="20" x2="${left}" y2="${totalHeight - 30}" class="forecast-axis" />
    <line x1="${left}" y1="${totalHeight - 30}" x2="${left + chartWidth}" y2="${totalHeight - 30}" class="forecast-axis" />
    ${bars}
  `;

  if (legend) {
    const topRoute = orderedRows[0] ? orderedRows[0].route : "—";
    legend.innerHTML = `
      <span class="forecast-legend-pill"><i class="forecast-legend-swatch"></i>Forecast values</span>
      <span class="forecast-legend-pill forecast-legend-pill-secondary">Routes: ${orderedRows.length}</span>
      <span class="forecast-legend-pill forecast-legend-pill-secondary">Top route: ${topRoute}</span>
    `;
  }
}

if (forecastHorizons) {
  forecastHorizons.querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => {
      setForecastDays(Number(button.dataset.days));
    });
  });
}

function loadForecast(days = defaultDays) {
  fetch(`/api/model-forecast?advance_days=${days}`)
    .then((response) => response.json().then((data) => ({ response, data })))
    .then(({ response, data }) => {
      if (!response.ok) throw new Error(data.error || "Forecast unavailable.");

      const rows = (data.routes || []).map((row) => ({
        route: row.route,
        horizon: `T+${row.advance_days}`,
        observed: row.latest_observed_day,
        forecast: row.forecast_value,
        model: row.model || "Recent median baseline",
        predictionSource: row.prediction_source || "baseline",
        note: row.prediction_source === "model"
          ? `Model-backed forecast for ${row.route} using the latest route and horizon features.`
          : `Forecast uses the latest observed median for ${row.route} at ${row.latest_observed_day}. This is a baseline estimate, not an observed fare.`,
      }));

      if (forecastRouteSelect) {
        const availableRoutes = [...new Set(rows.map((row) => row.route))];
        forecastRouteSelect.innerHTML = [
          '<option value="all">All routes</option>',
          ...availableRoutes.map((route) => `<option value="${route}">${route}</option>`),
        ].join("");
        if (!availableRoutes.includes(selectedRoute)) {
          selectedRoute = "all";
        }
        forecastRouteSelect.value = selectedRoute;
      }

      const filteredRows = selectedRoute === "all"
        ? rows
        : rows.filter((row) => row.route === selectedRoute);

      const isModelReady = Boolean(data.model_available);
      document.getElementById("forecastModel").textContent = isModelReady ? (data.model || "Trained fare model") : "Recent median baseline";
      document.getElementById("forecastStatus").textContent = filteredRows.length ? (isModelReady ? "Ready • model-backed" : "Ready • baseline fallback") : "Data shortfall";
      document.getElementById("forecastRoute").textContent = selectedRoute === "all" ? "All routes" : selectedRoute;
      document.getElementById("forecastHorizon").textContent = `T+${days}`;
      document.getElementById("forecastMeta").textContent = isModelReady
        ? `Model forecast is live for T+${days}${selectedRoute === "all" ? " across all tracked routes" : ` for ${selectedRoute}`}. Values are generated by the trained fare model and shown alongside route-horizon evidence.`
        : `Baseline forecast is a live recent-median estimate for T+${days}${selectedRoute === "all" ? " across all tracked routes" : ` for ${selectedRoute}`}. It is explicitly labelled as a forecast and is not an observed fare line.`;
      document.getElementById("forecastContext").innerHTML = `
        <span><b>Model</b> ${data.model || "Recent median baseline"}</span>
        <span><b>Forecast label</b> ${isModelReady ? "Predicted / model-backed" : "Predicted / baseline only"}</span>
        <span><b>Scope</b> ${selectedRoute === "all" ? "All tracked routes" : selectedRoute}</span>
      `;
      renderForecastChart(filteredRows);
      document.getElementById("forecastRows").innerHTML = filteredRows.map((row) => `
        <tr>
          <td>${row.route}</td>
          <td>${row.horizon}</td>
          <td>${row.observed}</td>
          <td>${money(row.forecast)}</td>
          <td>${row.note}</td>
        </tr>
      `).join("");
    })
    .catch((error) => {
      document.getElementById("forecastMeta").textContent = error.message;
      document.getElementById("forecastRows").innerHTML = `<tr><td colspan="5">${error.message}</td></tr>`;
    });
}

if (forecastRouteSelect) {
  forecastRouteSelect.addEventListener("change", () => {
    selectedRoute = forecastRouteSelect.value;
    loadForecast(activeDays);
  });
}

setForecastDays(defaultDays);
