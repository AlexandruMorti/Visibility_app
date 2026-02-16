// Prediction form handler
document.getElementById('form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const form = e.target;
  const data = Object.fromEntries(new FormData(form).entries());
  
  // Convert numeric fields; keep 'region' as string
  const numericKeys = ['lat','lon','swell_height','swell_period','wind_speed','wind_dir','tide_height','turbidity','chlorophyll'];
  for (const k of numericKeys) {
    if (data[k] && data[k].trim() !== '') {
      data[k] = parseFloat(data[k]);
    } else {
      delete data[k]; // Remove empty fields so backend can use Stormglass defaults
    }
  }
  
  const resDiv = document.getElementById('result');
  const hasLocation = data.lat !== undefined && data.lon !== undefined;
  resDiv.textContent = hasLocation ? 'Fetching Stormglass data and predicting...' : 'Predicting...';
  resDiv.style.display = 'block';
  
  try {
    const r = await fetch('/predict', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    const json = await r.json();
    if (r.ok) {
      const region = json.region || data.region || 'GLOBAL';
      const dataSource = json.data_source === 'hybrid' ? ' (Stormglass + manual)' : '';
      resDiv.innerHTML = `<strong>Region ${region}:</strong> Predicted visibility <strong>${json.visibility_m.toFixed(2)} m</strong>${dataSource}`;
      
      // Show the features used if available
      if (json.features && json.data_source === 'hybrid') {
        const features = json.features;
        resDiv.innerHTML += `<div style="font-size:12px; margin-top:8px; color:#666;">📊 Used: Swell ${features.swell_height.toFixed(1)}m/${features.swell_period.toFixed(1)}s, Wind ${features.wind_speed_ms.toFixed(1)}m/s @ ${features.wind_dir.toFixed(0)}°, Tide ${features.tide_height.toFixed(2)}m, Turbidity ${features.turbidity.toFixed(2)}, Chlorophyll ${features.chlorophyll.toFixed(2)}mg/m³</div>`;
      }
    } else {
      resDiv.textContent = `Error: ${json.error || JSON.stringify(json)}`;
    }
  } catch (err) {
    resDiv.textContent = 'Request failed: ' + err;
  }
});
