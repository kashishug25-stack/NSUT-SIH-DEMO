const defaultDays = 7;
let selectedDays = defaultDays;

function formatValue(value) {
  return value == null ? '-' : Number(value).toFixed(2);
}

function renderChart(table) {
  const svg = document.getElementById('cpiChart');
  const legend = document.getElementById('cpiLegend');
  if (!svg) return;

  const rows = (table || []).filter((row) => row.api_index != null || row.cpi_index != null);
  if (!rows.length) {
    svg.innerHTML = '<text x="550" y="170" text-anchor="middle" class="chart-label">No comparison data</text>';
    if (legend) legend.innerHTML = '';
    return;
  }

  if (legend) {
    legend.innerHTML = `
      <span><i style="background:#f17844"></i>APIx</span>
      <span><i style="background:#6d8570"></i>CPI reference</span>
    `;
  }

  const left = 62;
  const top = 24;
  const width = 980;
  const height = 260;
  const allValues = rows.flatMap((row) => [row.api_index, row.cpi_index]).filter((value) => value != null);
  const maxValue = Math.max(...allValues, 100);
  const minValue = Math.min(...allValues, 100);

  const x = (index) => left + (index * (width / Math.max(rows.length - 1, 1)));
  const y = (value) => top + height - ((value - minValue) / Math.max((maxValue - minValue) || 1, 1)) * height;

  const apiPath = rows.map((row, index) => `${index === 0 ? 'M' : 'L'}${x(index)},${y(row.api_index ?? minValue)}`).join(' ');
  const cpiPath = rows.map((row, index) => `${index === 0 ? 'M' : 'L'}${x(index)},${y(row.cpi_index ?? minValue)}`).join(' ');

  const grid = [0, 0.25, 0.5, 0.75, 1].map((step) => {
    const value = minValue + ((maxValue - minValue) * step);
    const yPos = y(value);
    return `
      <line x1="${left}" y1="${yPos}" x2="${left + width}" y2="${yPos}" class="chart-grid" />
      <text x="${left - 10}" y="${yPos + 4}" text-anchor="end" class="chart-label">${value.toFixed(1)}</text>
    `;
  }).join('');

  const pointsMarkup = rows.map((row, index) => `
    <text x="${x(index)}" y="${top + height + 22}" text-anchor="middle" class="chart-label">${row.month.slice(5)}</text>
  `).join('');

  svg.innerHTML = `
    <line x1="${left}" x2="${left + width}" y1="${top + height}" y2="${top + height}" class="chart-grid" />
    ${grid}
    <path d="${apiPath}" class="chart-line" style="stroke:#f17844;" />
    <path d="${cpiPath}" class="chart-line" style="stroke:#6d8570; stroke-dasharray: 6 6;" />
    ${pointsMarkup}
  `;
}

function renderRows(table) {
  const tbody = document.getElementById('cpiRows');
  if (!tbody) return;

  tbody.innerHTML = (table || []).map((row) => `
    <tr>
      <td>${row.month}</td>
      <td>${formatValue(row.api_index)}</td>
      <td>${formatValue(row.cpi_index)}</td>
      <td>${formatValue(row.api_inflation)}</td>
      <td>${formatValue(row.cpi_inflation)}</td>
      <td>${formatValue(row.api_yoy)}</td>
      <td>${formatValue(row.cpi_yoy)}</td>
    </tr>
  `).join('');
}

function load(days) {
  selectedDays = days;

  const buttons = document.querySelectorAll('#cpiHorizons button');
  buttons.forEach((button) => {
    button.classList.toggle('active', Number(button.dataset.days) === days);
  });

  fetch(`/api/cpi-comparison?advance_days=${days}`)
    .then((response) => response.json().then((data) => ({ response, data })))
    .then(({ response, data }) => {
      if (!response.ok) throw new Error(data.error || 'CPI comparison unavailable.');

      const latestApi = (data.api_series || []).slice(-1)[0];
      const latestCpi = (data.cpi_series || []).slice(-1)[0];

      document.getElementById('cpiHorizon').textContent = `T+${days}`;
      document.getElementById('cpiApiLatest').textContent = latestApi ? formatValue(latestApi.api_rebased) : '-';
      document.getElementById('cpiCpiLatest').textContent = latestCpi ? formatValue(latestCpi.cpi_rebased) : '-';
      document.getElementById('cpiWeighting').textContent = data.weight_status || '-';
      document.getElementById('cpiContext').innerHTML = `
        <span><b>Comparison</b> APIx vs MoSPI CPI reference</span>
        <span><b>Weighting</b> ${data.weight_status}</span>
        <span><b>Notes</b> ${data.notes?.[0] || 'Comparison uses workspace reference data.'}</span>
      `;
      document.getElementById('cpiMeta').textContent = `Monthly rebased comparison for T+${days}. APIx is calculated from live database values and the MoSPI CPI reference is shown as a separate proxy series.`;

      renderChart(data.table || []);
      renderRows(data.table || []);
    })
    .catch((error) => {
      document.getElementById('cpiMeta').textContent = error.message;
      document.getElementById('cpiContext').innerHTML = '<span><b>Status</b> unavailable</span>';
      document.getElementById('cpiRows').innerHTML = `<tr><td colspan="7">${error.message}</td></tr>`;
      document.getElementById('cpiChart').innerHTML = '<text x="550" y="170" text-anchor="middle" class="chart-label">Comparison unavailable</text>';
    });
}

function setup() {
  document.querySelectorAll('#cpiHorizons button[data-days]').forEach((button) => {
    button.addEventListener('click', () => load(Number(button.dataset.days)));
  });

  load(selectedDays);
}

setup();
