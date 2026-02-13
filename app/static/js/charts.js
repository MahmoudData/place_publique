/**
 * Place Publique — Dashboard charts
 * Dépend de Chart.js + chartjs-adapter-date-fns (chargés via CDN)
 */

let chart        = null;
let statsChart   = null;
let currentHours = 24;
let currentId    = null;
let refreshTimer = null;
let currentStatsPeriod = 'hourly';
let currentStatsClass  = 'person';

// Libellés français pour le titre du graphique
const CLASS_LABELS = {
  person:     'personnes',
  bicycle:    'vélos',
  car:        'voitures',
  motorcycle: 'motos',
  truck:      'camions',
};

// Couleurs cohérentes avec app.py
const CLASS_COLORS = {
  person:     { bg: 'rgba(54,  162, 235, 0.6)', border: 'rgba(54,  162, 235, 0.9)' },
  bicycle:    { bg: 'rgba(75,  192, 192, 0.6)', border: 'rgba(75,  192, 192, 0.9)' },
  car:        { bg: 'rgba(255,  99, 132, 0.6)', border: 'rgba(255,  99, 132, 0.9)' },
  motorcycle: { bg: 'rgba(255, 159,  64, 0.6)', border: 'rgba(255, 159,  64, 0.9)' },
  truck:      { bg: 'rgba(153, 102, 255, 0.6)', border: 'rgba(153, 102, 255, 0.9)' },
};

// ---------------------------------------------------------------------------
// Sélection webcam
// ---------------------------------------------------------------------------

document.querySelectorAll('.webcam-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    // Highlight bouton actif
    document.querySelectorAll('.webcam-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    // Mettre à jour les infos d'en-tête
    currentId = parseInt(btn.dataset.id, 10);
    document.getElementById('dash-name').textContent = btn.dataset.name;
    document.getElementById('dash-location').textContent = btn.dataset.location;

    // Afficher le dashboard
    document.getElementById('dashboard').classList.remove('d-none');

    // Réinitialiser la période
    document.querySelectorAll('#period-selector button').forEach(b => b.classList.remove('active'));
    document.querySelector('#period-selector button[data-hours="24"]').classList.add('active');
    currentHours = 24;

    // Détruire les charts précédents si besoin
    if (chart) { chart.destroy(); chart = null; }
    if (statsChart) { statsChart.destroy(); statsChart = null; }

    // Réinitialiser période et classe stats
    document.querySelectorAll('#stats-period-selector button').forEach(b => b.classList.remove('active'));
    document.querySelector('#stats-period-selector button[data-period="hourly"]').classList.add('active');
    currentStatsPeriod = 'hourly';

    document.querySelectorAll('#stats-class-selector button').forEach(b => b.classList.remove('active'));
    document.querySelector('#stats-class-selector button[data-class="person"]').classList.add('active');
    currentStatsClass = 'person';
    document.getElementById('stats-class-label').textContent = CLASS_LABELS['person'];

    refresh();
    refreshStats();
    startAutoRefresh();
  });
});

// ---------------------------------------------------------------------------
// Sélecteur de période
// ---------------------------------------------------------------------------

document.querySelectorAll('#period-selector button').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('#period-selector button').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentHours = parseInt(btn.dataset.hours, 10);
    refresh();
  });
});

// ---------------------------------------------------------------------------
// Fetch + rendu
// ---------------------------------------------------------------------------

async function loadData(webcamId, hours) {
  const resp = await fetch(`/api/detections/${webcamId}?hours=${hours}`);
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return resp.json();
}

function buildChart(data) {
  const ctx    = document.getElementById('detectionChart');
  const noData = document.getElementById('no-data');

  if (!data.labels || data.labels.length === 0) {
    ctx.classList.add('d-none');
    noData.classList.remove('d-none');
    updateSummary([]);
    return;
  }

  ctx.classList.remove('d-none');
  noData.classList.add('d-none');

  if (chart) {
    chart.data.labels   = data.labels;
    chart.data.datasets = data.datasets;
    chart.update();
  } else {
    chart = new Chart(ctx, {
      type: 'line',
      data: { labels: data.labels, datasets: data.datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { position: 'bottom' },
          tooltip: {
            callbacks: {
              title: (items) => new Date(items[0].label).toLocaleString('fr-FR'),
            },
          },
        },
        scales: {
          x: {
            type: 'time',
            time: { tooltipFormat: 'dd/MM HH:mm', displayFormats: { hour: 'dd/MM HH:mm', day: 'dd/MM' } },
            ticks: { maxTicksLimit: 10, color: '#6c757d' },
            grid:  { color: 'rgba(0,0,0,.05)' },
          },
          y: {
            beginAtZero: true,
            ticks: { precision: 0, color: '#6c757d' },
            grid:  { color: 'rgba(0,0,0,.05)' },
            title: { display: true, text: 'Nombre détecté', color: '#6c757d' },
          },
        },
      },
    });
  }

  updateSummary(data.datasets);
}

function updateSummary(datasets) {
  const tbody = document.getElementById('summary-body');
  if (!datasets || datasets.length === 0) {
    tbody.innerHTML = '<tr><td colspan="3" class="text-center text-secondary py-3">Aucune donnée</td></tr>';
    return;
  }
  tbody.innerHTML = datasets.map(ds => {
    const vals = ds.data.filter(v => v > 0);
    const max  = vals.length ? Math.max(...vals) : 0;
    const avg  = vals.length ? (vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(1) : '–';
    return `<tr>
      <td><span class="badge rounded-pill" style="background:${ds.borderColor}">${ds.label}</span></td>
      <td class="text-end">${max}</td>
      <td class="text-end">${avg}</td>
    </tr>`;
  }).join('');
}

function refreshImage(imageUrl) {
  const container = document.getElementById('last-image-container');

  if (!imageUrl) {
    container.innerHTML = `<div class="text-center text-secondary py-4"><i class="bi bi-image fs-2"></i><p class="mt-2 small">Image non disponible</p></div>`;
    return;
  }

  // Cache-buster pour forcer le rechargement à chaque refresh
  const url = `${imageUrl}?ts=${Date.now()}`;
  const img = new Image();
  img.onload = () => {
    container.innerHTML = `<img src="${url}" class="img-fluid w-100 rounded-bottom" alt="Dernière détection" id="last-image">`;
  };
  img.onerror = () => {
    container.innerHTML = `<div class="text-center text-secondary py-4"><i class="bi bi-image fs-2"></i><p class="mt-2 small">Image non disponible</p></div>`;
  };
  img.src = url;
}

function updateLastUpdate() {
  const el = document.getElementById('last-update');
  if (el) el.textContent = 'Mis à jour ' + new Date().toLocaleTimeString('fr-FR');
}

// ---------------------------------------------------------------------------
// Cycle de refresh
// ---------------------------------------------------------------------------

async function refresh() {
  if (currentId === null) return;
  try {
    const data = await loadData(currentId, currentHours);
    buildChart(data);
    updateLastUpdate();
    refreshImage(data.last_image_url || null);
  } catch (err) {
    console.error('Erreur chargement données :', err);
  }
}

function startAutoRefresh() {
  if (refreshTimer) clearInterval(refreshTimer);
  refreshTimer = setInterval(() => { refresh(); refreshStats(); }, 5 * 60 * 1000);
}

// ---------------------------------------------------------------------------
// Sélecteurs stats (période + classe)
// ---------------------------------------------------------------------------

document.querySelectorAll('#stats-period-selector button').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('#stats-period-selector button').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentStatsPeriod = btn.dataset.period;
    refreshStats();
  });
});

document.querySelectorAll('#stats-class-selector button').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('#stats-class-selector button').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentStatsClass = btn.dataset.class;
    document.getElementById('stats-class-label').textContent = CLASS_LABELS[currentStatsClass] || currentStatsClass;
    // Détruire le chart pour forcer une recréation avec la nouvelle couleur
    if (statsChart) { statsChart.destroy(); statsChart = null; }
    refreshStats();
  });
});

// ---------------------------------------------------------------------------
// Stats fetch + rendu (bar chart)
// ---------------------------------------------------------------------------

async function loadStats(webcamId, period, className) {
  const resp = await fetch(`/api/stats/${webcamId}?period=${period}&class=${className}`);
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return resp.json();
}

function buildStatsChart(data) {
  const ctx    = document.getElementById('statsChart');
  const noData = document.getElementById('stats-no-data');

  if (!data.labels || data.labels.length === 0) {
    ctx.classList.add('d-none');
    noData.classList.remove('d-none');
    return;
  }

  ctx.classList.remove('d-none');
  noData.classList.add('d-none');

  const cls    = data.class_name || 'person';
  const colors = CLASS_COLORS[cls] || { bg: 'rgba(100,100,100,0.6)', border: 'rgba(100,100,100,0.9)' };
  const label  = CLASS_LABELS[cls] || cls;
  const yLabel = data.period === 'hourly' ? `Moy. ${label}` : `Total ${label}`;

  if (statsChart) {
    statsChart.data.labels                         = data.labels;
    statsChart.data.datasets[0].data               = data.data;
    statsChart.data.datasets[0].label              = label;
    statsChart.data.datasets[0].backgroundColor    = colors.bg;
    statsChart.data.datasets[0].borderColor        = colors.border;
    statsChart.options.scales.y.title.text         = yLabel;
    statsChart.update();
  } else {
    statsChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: data.labels,
        datasets: [{
          label:           label,
          data:            data.data,
          backgroundColor: colors.bg,
          borderColor:     colors.border,
          borderWidth: 1,
          borderRadius: 4,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
        },
        scales: {
          x: {
            ticks: { color: '#6c757d', maxRotation: 45 },
            grid:  { color: 'rgba(0,0,0,.05)' },
          },
          y: {
            beginAtZero: true,
            ticks: { precision: 0, color: '#6c757d' },
            grid:  { color: 'rgba(0,0,0,.05)' },
            title: { display: true, text: yLabel, color: '#6c757d' },
          },
        },
      },
    });
  }
}

async function refreshStats() {
  if (currentId === null) return;
  try {
    const data = await loadStats(currentId, currentStatsPeriod, currentStatsClass);
    buildStatsChart(data);
  } catch (err) {
    console.error('Erreur chargement stats :', err);
  }
}
