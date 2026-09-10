const defaultDays = 7;
let selectedDays = defaultDays;

function formatMoney(value) {
  return value == null ? "-" : `₹${Math.round(value).toLocaleString("en-IN")}`;
}

function setStatus(message, isError = false) {
  const meta = document.getElementById("apixMeta");
  if (meta) {
    meta.textContent = message;
    meta.style.color = isError ? "#e11d48" : "#64748b";
  }
}

function renderChart(points) {
  const svg = document.getElementById("apixChart");
  if (!svg) return;

  const safePoints = (points || []).map((point) => ({
    label: point.observed_day,
    value: Number(point.index_value),
  })).filter((point) => Number.isFinite(point.value));

  if (!safePoints.length) {
    svg.innerHTML = '<text x="550" y="170" text-anchor="middle" class="chart-label">No APIx observations</text>';
    return;
  }

  const left = 60;
  const top = 22;
  const width = 980;
  const height = 260;
  const maxValue = Math.max(...safePoints.map((point) => point.value), 100);
  const minValue = Math.min(...safePoints.map((point) => point.value), 100);

  const y = (value) => top + height - ((value - minValue) / Math.max((maxValue - minValue) || 1, 1)) * height;
  const x = (index) => left + (index * (width / Math.max(safePoints.length - 1, 1)));

  const areaPath = safePoints.map((point, index) => `${index === 0 ? "M" : "L"}${x(index)},${y(point.value)}`).join(" ");
  const linePath = safePoints.map((point, index) => `${index === 0 ? "M" : "L"}${x(index)},${y(point.value)}`).join(" ");

  const horizontalGrid = [0, 0.25, 0.5, 0.75, 1].map((step) => {
    const value = minValue + ((maxValue - minValue) * step);
    const yPos = y(value);
    return `
      <line x1="${left}" y1="${yPos}" x2="${left + width}" y2="${yPos}" class="chart-grid" />
      <text x="${left - 10}" y="${yPos + 4}" text-anchor="end" class="chart-label">${value.toFixed(1)}</text>
    `;
  }).join("");

  const pointsMarkup = safePoints.map((point, index) => `
    <circle cx="${x(index)}" cy="${y(point.value)}" r="4.5" class="chart-dot" fill="#e36b45" />
    <text x="${x(index)}" y="${top + height + 22}" text-anchor="middle" class="chart-label">${point.label.slice(5)}</text>
  `).join("");

  svg.innerHTML = `
    <line x1="${left}" x2="${left + width}" y1="${top + height}" y2="${top + height}" class="chart-grid" />
    ${horizontalGrid}
    <path d="${areaPath} L ${x(safePoints.length - 1)},${top + height} L ${x(0)},${top + height} Z" fill="rgba(227,107,69,0.10)" />
    <path d="${linePath}" class="chart-line" style="stroke:#e36b45;" />
    ${pointsMarkup}
  `;
}

function renderRows(points) {
  const tbody = document.getElementById("apixRows");
  if (!tbody) return;

  tbody.innerHTML = (points || []).map((point) => `
    <tr>
      <td>${point.observed_day}</td>
      <td>${Number(point.index_value).toFixed(2)}</td>
    </tr>
  `).join("");
}

function load(days) {
  selectedDays = days;

  const horizonButtons = document.querySelectorAll("#apixHorizons button");
  horizonButtons.forEach((button) => {
    button.classList.toggle("active", Number(button.dataset.days) === days);
  });

  Promise.all([
    fetch(`/api/index?advance_days=${days}`).then((response) => response.json().then((data) => ({ response, data }))),
    fetch(`/api/index-series?advance_days=${days}`).then((response) => response.json().then((data) => ({ response, data }))),
  ])
    .then(([indexResponse, seriesResponse]) => {
      if (!indexResponse.response.ok) throw new Error(indexResponse.data.error || "Index unavailable.");
      if (!seriesResponse.response.ok) throw new Error(seriesResponse.data.error || "Index series unavailable.");

      const indexData = indexResponse.data;
      const seriesData = seriesResponse.data;

      document.getElementById("apixValue").textContent = Number(indexData.index_value).toFixed(2);
      document.getElementById("apixBase").textContent = indexData.base_period;
      document.getElementById("apixCurrent").textContent = indexData.current_period;
      document.getElementById("apixCoverage").textContent = `${indexData.route_count} routes`;

      document.getElementById("apixContext").innerHTML = `
        <span><b>Horizon</b> T+${days}</span>
        <span><b>Weighting</b> ${indexData.weight_status}</span>
        <span><b>Base period</b> ${indexData.base_period}</span>
        <span><b>Current period</b> ${indexData.current_period}</span>
      `;

      document.getElementById("apixMeta").textContent = `Daily observed APIx values for T+${days} using the traffic-weighted route basket.`;
      document.getElementById("apixMeta").style.color = "#64748b";
      renderChart(seriesData.points || []);
      renderRows(seriesData.points || []);
    })
    .catch((error) => {
      setStatus(error.message, true);
      document.getElementById("apixValue").textContent = "Unavailable";
      document.getElementById("apixBase").textContent = "—";
      document.getElementById("apixCurrent").textContent = "—";
      document.getElementById("apixCoverage").textContent = "—";
      document.getElementById("apixRows").innerHTML = `<tr><td colspan="2">${error.message}</td></tr>`;
      document.getElementById("apixChart").innerHTML = '<text x="550" y="170" text-anchor="middle" class="chart-label">Index unavailable</text>';
    });
}

function setup() {
  document.querySelectorAll("#apixHorizons button[data-days]").forEach((button) => {
    button.addEventListener("click", () => load(Number(button.dataset.days)));
  });

  load(selectedDays);
}

setup();
