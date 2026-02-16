// Weather card handler
const weatherBtn = document.getElementById('weather-btn');
if (weatherBtn) {
  weatherBtn.addEventListener('click', async () => {
    const latEl = document.getElementById('weather-lat');
    const lonEl = document.getElementById('weather-lon');
    const outEl = document.getElementById('weather-output');
    const lat = parseFloat(latEl.value);
    const lon = parseFloat(lonEl.value);
    outEl.textContent = 'Fetching weather...';
    outEl.style.display = 'block';
    try {
      const r = await fetch('/weather', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lat, lon }),
      });
      const json = await r.json();
      if (!r.ok) {
        outEl.textContent = `Error: ${json.error || JSON.stringify(json)}`;
        return;
      }
      const parts = [];
      if (json.time) parts.push(`⏰ Time: ${json.time}`);
      if (json.temperature_2m !== undefined && json.temperature_2m !== null) parts.push(`🌡️ Temp: ${json.temperature_2m} °C`);
      if (json.wind_speed_knots !== undefined && json.wind_speed_knots !== null) parts.push(`💨 Wind: ${json.wind_speed_knots} kt`);
      if (json.wind_direction_deg !== undefined && json.wind_direction_deg !== null) parts.push(`🧭 Dir: ${json.wind_direction_deg}°`);
      outEl.textContent = parts.join(' | ');
    } catch (err) {
      outEl.textContent = 'Request failed: ' + err;
    }
  });
}

// Fetch weather and immediately predict using current form values,
// overriding wind speed (knots) and wind direction from weather.
const weatherPredictBtn = document.getElementById('weather-predict-btn');
if (weatherPredictBtn) {
  weatherPredictBtn.addEventListener('click', async () => {
    const latEl = document.getElementById('weather-lat');
    const lonEl = document.getElementById('weather-lon');
    const outEl = document.getElementById('weather-output');
    const lat = parseFloat(latEl.value);
    const lon = parseFloat(lonEl.value);
    outEl.textContent = 'Fetching weather and predicting...';
    outEl.style.display = 'block';
    
    try {
      const r = await fetch('/weather', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lat, lon }),
      });
      const weather = await r.json();
      if (!r.ok) {
        outEl.textContent = `Error: ${weather.error || JSON.stringify(weather)}`;
        return;
      }
      
      // Show weather data
      const parts = [];
      if (weather.time) parts.push(`⏰ ${weather.time}`);
      if (weather.temperature_2m !== undefined) parts.push(`🌡️ ${weather.temperature_2m}°C`);
      if (weather.wind_speed_knots !== undefined) parts.push(`💨 ${weather.wind_speed_knots} kt`);
      if (weather.wind_direction_deg !== undefined) parts.push(`🧭 ${weather.wind_direction_deg}°`);
      
      // Now predict with the weather data
      const predictData = {
        region: 'UK',
        lat: lat,
        lon: lon,
        wind_speed: weather.wind_speed_knots || 6.0,
        wind_dir: weather.wind_direction_deg || 180
      };
      
      const predictR = await fetch('/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(predictData),
      });
      const predictJson = await predictR.json();
      
      if (predictR.ok) {
        const visibility = predictJson.visibility_m ? predictJson.visibility_m.toFixed(2) : 'N/A';
        outEl.innerHTML = `
          <div><strong>Weather:</strong> ${parts.join(' | ')}</div>
          <div style="margin-top:0.75rem"><strong>🔮 Predicted Visibility:</strong> ${visibility} m</div>
        `;
      } else {
        outEl.innerHTML = `
          <div><strong>Weather:</strong> ${parts.join(' | ')}</div>
          <div style="margin-top:0.75rem; color:#c62828;">Prediction Error: ${predictJson.error || JSON.stringify(predictJson)}</div>
        `;
      }
    } catch (err) {
      outEl.textContent = 'Request failed: ' + err;
    }
  });
}

// Stormglass predict button
const stormglassPredictBtn = document.getElementById('stormglass-predict-btn');
if (stormglassPredictBtn) {
  stormglassPredictBtn.addEventListener('click', async () => {
    const latEl = document.getElementById('weather-lat');
    const lonEl = document.getElementById('weather-lon');
    const outEl = document.getElementById('weather-output');
    const autoTurbidityCheckbox = document.getElementById('auto-turbidity');
    const lat = parseFloat(latEl.value);
    const lon = parseFloat(lonEl.value);
    
    outEl.textContent = 'Fetching Stormglass data and predicting...';
    outEl.style.display = 'block';
    
    const payload = {
      region: 'UK',
      lat: lat,
      lon: lon
    };
    
    if (autoTurbidityCheckbox && autoTurbidityCheckbox.checked) {
      payload.auto_turbidity = true;
    }
    
    try {
      const r = await fetch('/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const json = await r.json();
      
      if (r.ok) {
        const visibility = json.visibility_m ? json.visibility_m.toFixed(2) : 'N/A';
        const region = json.region || 'UK';
        const dataSource = json.data_source === 'hybrid' ? ' (Stormglass + manual)' : json.data_source === 'stormglass' ? ' (Stormglass)' : '';
        
        let output = `<div><strong>Region ${region}:</strong> Predicted visibility <strong>${visibility} m</strong>${dataSource}</div>`;
        
        // Show the features used if available
        if (json.features && json.data_source) {
          const features = json.features;
          output += `<div style="font-size:0.9rem; margin-top:0.75rem; color:#666;">
            📊 <strong>Used data:</strong><br>
            🌊 Swell: ${features.swell_height.toFixed(1)}m / ${features.swell_period.toFixed(1)}s<br>
            💨 Wind: ${features.wind_speed_ms.toFixed(1)}m/s @ ${features.wind_dir.toFixed(0)}°<br>
            🌀 Tide: ${features.tide_height.toFixed(2)}m<br>
            💧 Turbidity: ${features.turbidity.toFixed(2)}<br>
            🟢 Chlorophyll: ${features.chlorophyll.toFixed(2)}mg/m³
          </div>`;
        }
        
        outEl.innerHTML = output;
      } else {
        outEl.textContent = `Error: ${json.error || JSON.stringify(json)}`;
      }
    } catch (err) {
      outEl.textContent = 'Request failed: ' + err;
    }
  });
}

// Preset buttons to populate lat/lon
document.querySelectorAll('.preset-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const lat = parseFloat(btn.getAttribute('data-lat'));
    const lon = parseFloat(btn.getAttribute('data-lon'));
    
    // Update weather section lat/lon
    const weatherLatEl = document.getElementById('weather-lat');
    const weatherLonEl = document.getElementById('weather-lon');
    if (!Number.isNaN(lat)) weatherLatEl.value = lat.toFixed(4);
    if (!Number.isNaN(lon)) weatherLonEl.value = lon.toFixed(4);
  });
});
