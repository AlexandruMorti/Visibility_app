// --- Dive map and table ---
async function fetchAndRenderDives(map) {
  try {
    const r = await fetch('/dives');
    const dives = await r.json();
    const tbody = document.querySelector('#dives-table tbody');
    const statusEl = document.getElementById('dive-status');
    tbody.innerHTML = '';
    if (!Array.isArray(dives)) {
      if (statusEl) statusEl.textContent = 'Unexpected response from /dives';
      return;
    }
    if (dives.length === 0) {
      if (statusEl) statusEl.textContent = 'No dives recorded yet.';
      tbody.innerHTML = '<tr><td colspan="11" style="text-align:center; padding:2rem;"><div class="empty-state"><div class="empty-state-icon">🤿</div><div>No dives logged yet. Click on the map to add your first dive!</div></div></td></tr>';
    } else {
      if (statusEl) statusEl.textContent = `Loaded ${dives.length} dive(s)`;
    }

    // If we have a Leaflet marker layer, clear it
    if (map && window._diveMarkerLayer && typeof window._diveMarkerLayer.clearLayers === 'function') {
      window._diveMarkerLayer.clearLayers();
    }

    for (const d of dives.slice().reverse()) {
      const tr = document.createElement('tr');
      const date = d.date ? d.date.split('T')[0] : '';
      tr.innerHTML = `<td>${date}</td><td>${d.lat.toFixed(4)}</td><td>${d.lon.toFixed(4)}</td><td>${d.depth===undefined||d.depth===null? '': d.depth}</td><td>${d.breath_hold_time===undefined||d.breath_hold_time===null? '': d.breath_hold_time}</td><td>${d.tide_height===undefined||d.tide_height===null? '': d.tide_height}</td><td>${d.visibility===undefined||d.visibility===null? '': d.visibility}</td><td>${d.water_temp===undefined||d.water_temp===null? '': d.water_temp}</td><td>${d.outside_temp===undefined||d.outside_temp===null? '': d.outside_temp}</td><td>${(d.notes||'').replace(/</g,'&lt;')}</td><td><button class="edit-dive-btn" data-dive-id="${d.id}">Edit</button></td>`;
      tbody.appendChild(tr);
      if (map && typeof L !== 'undefined') {
        try {
          const popupText = `<strong>${date}</strong><br>Depth: ${d.depth||'N/A'}m<br>Breath hold: ${d.breath_hold_time||'N/A'}s<br>Tide: ${d.tide_height||'N/A'}m<br>Visibility: ${d.visibility||'N/A'}m<br>Water temp: ${d.water_temp||'N/A'}°C<br>Air temp: ${d.outside_temp||'N/A'}°C<br>${(d.notes||'')}`;
          const m = L.marker([d.lat, d.lon]).bindPopup(popupText);
          if (window._diveMarkerLayer && typeof window._diveMarkerLayer.addLayer === 'function') {
            window._diveMarkerLayer.addLayer(m);
          } else {
            m.addTo(map);
          }
        } catch (e) {}
      }
    }
    
    // Add event listeners to edit buttons
    document.querySelectorAll('.edit-dive-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const diveId = e.target.getAttribute('data-dive-id');
        const dive = dives.find(d => d.id === diveId);
        if (!dive) return;
        
        const date = prompt('Date (YYYY-MM-DD)', dive.date ? dive.date.split('T')[0] : '');
        if (date === null) return;
        const depth = prompt('Depth (m)', dive.depth || '');
        if (depth === null) return;
        const breathHold = prompt('Breath hold (s)', dive.breath_hold_time || '');
        if (breathHold === null) return;
        const tideHeight = prompt('Tide height (m)', dive.tide_height || '');
        if (tideHeight === null) return;
        const visibility = prompt('Visibility (m)', dive.visibility || '');
        if (visibility === null) return;
        const waterTemp = prompt('Water temperature (°C)', dive.water_temp || '');
        if (waterTemp === null) return;
        const outsideTemp = prompt('Air temperature (°C)', dive.outside_temp || '');
        if (outsideTemp === null) return;
        const notes = prompt('Notes', dive.notes || '');
        if (notes === null) return;
        
        const payload = {
          date: date || undefined,
          depth: depth || undefined,
          breath_hold_time: breathHold || undefined,
          tide_height: tideHeight || undefined,
          visibility: visibility || undefined,
          water_temp: waterTemp || undefined,
          outside_temp: outsideTemp || undefined,
          notes: notes || undefined
        };
        
        try {
          const r = await fetch(`/dives/${diveId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
          });
          if (r.ok) {
            await fetchAndRenderDives(map);
            alert('Dive updated successfully! 🎉');
          } else {
            const j = await r.json();
            alert('Failed to update dive: ' + (j.error || JSON.stringify(j)));
          }
        } catch (err) {
          alert('Request failed: ' + err);
        }
      });
    });
  } catch (err) {
    console.warn('Failed to load dives', err);
    const statusEl = document.getElementById('dive-status');
    if (statusEl) statusEl.textContent = 'Failed to load dives: ' + err;
  }
}

function initDiveMap() {
  if (typeof L === 'undefined') return null;
  const mapEl = document.getElementById('dive-map');
  if (!mapEl) return null;
  const statusEl = document.getElementById('dive-status');
  if (statusEl) statusEl.textContent = 'Initializing map...';

  const map = L.map(mapEl).setView([49.2138, -2.1358], 8);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 18,
    attribution: '© OpenStreetMap contributors'
  }).addTo(map);

  // marker layer for easier management
  window._diveMarkerLayer = L.layerGroup().addTo(map);

  if (statusEl) statusEl.textContent = 'Map initialized. Click to add dives.';

  // Load and render existing dives
  fetchAndRenderDives(map);

  map.on('click', async (ev) => {
    const lat = ev.latlng.lat;
    const lon = ev.latlng.lng;
    const date = prompt('Date for dive (YYYY-MM-DD) — leave empty for today', new Date().toISOString().slice(0,10));
    if (date === null) return; // cancelled
    const depth = prompt('Depth in meters (optional)');
    if (depth === null) return; // cancelled
    const breathHold = prompt('Max breath hold time in seconds (optional)');
    if (breathHold === null) return; // cancelled
    const tideHeight = prompt('Tide height in meters (optional)');
    if (tideHeight === null) return; // cancelled
    const visibility = prompt('Visibility in meters (optional)');
    if (visibility === null) return; // cancelled
    const waterTemp = prompt('Water temperature in °C (optional)');
    if (waterTemp === null) return; // cancelled
    const outsideTemp = prompt('Outside/air temperature in °C (optional)');
    if (outsideTemp === null) return; // cancelled
    const notes = prompt('Notes (optional)');
    if (notes === null) return; // cancelled
    const payload = { 
      lat, 
      lon, 
      date: date || undefined, 
      depth: (depth ? depth : undefined), 
      breath_hold_time: (breathHold ? breathHold : undefined),
      tide_height: (tideHeight ? tideHeight : undefined),
      visibility: (visibility ? visibility : undefined),
      water_temp: (waterTemp ? waterTemp : undefined),
      outside_temp: (outsideTemp ? outsideTemp : undefined),
      notes: (notes ? notes : undefined) 
    };
    try {
      const r = await fetch('/dives', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
      });
      if (r.status === 201) {
        // re-render
        if (window._diveMarkerLayer && typeof window._diveMarkerLayer.clearLayers === 'function') {
          window._diveMarkerLayer.clearLayers();
        }
        await fetchAndRenderDives(map);
        alert('Dive saved successfully! 🎉');
      } else {
        const j = await r.json();
        alert('Failed to save dive: ' + (j.error || JSON.stringify(j)));
      }
    } catch (err) {
      alert('Request failed: ' + err);
    }
  });

  return map;
}

document.addEventListener('DOMContentLoaded', () => {
  try {
    window._diveMap = initDiveMap();
  } catch (e) {
    console.warn('Dive map init failed', e);
    const statusEl = document.getElementById('dive-status');
    if (statusEl) statusEl.textContent = 'Failed to initialize map: ' + e.message;
  }
});

fetch("/dives_data")
    .then(res => res.json())
    .then(data => {
        const list = document.getElementById("dives-list");

        if (data.dives.length === 0) {
            list.innerHTML = "<p>No dives logged yet.</p>";
            return;
        }

        list.innerHTML = data.dives.map(d => `
            <div class="dive-entry">
                <strong>📍 ${d.lat.toFixed(4)}, ${d.lon.toFixed(4)}</strong><br>
                Visibility: <strong>${d.visibility} m</strong><br>
                Date: ${new Date(d.timestamp).toLocaleString()}<br>
                Notes: ${d.notes || "—"}
                <hr>
            </div>
        `).join("");
    });
