let lastPrediction = null;

// Handle form submission
document.getElementById("form").addEventListener("submit", function (e) {
    e.preventDefault();

    const formData = new FormData(e.target);
    const payload = Object.fromEntries(formData.entries());

    fetch("/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(response => {
        lastPrediction = response; // store Stormglass coords

        if (response.error) {
            document.getElementById("result").innerHTML =
                `<div class="error">${response.error}</div>`;
            return;
        }

        document.getElementById("result").innerHTML = `
            <h2>Predicted Visibility</h2>
            <p><strong>${response.visibility_m.toFixed(1)} meters</strong></p>
        `;
    })
    .catch(err => {
        document.getElementById("result").innerHTML =
            `<div class="error">Error: ${err}</div>`;
    });
});

// Stormglass autofill button
document.getElementById("use-stormglass-btn").addEventListener("click", function () {
    if (!lastPrediction || !lastPrediction.stormglass_coords) {
        alert("No Stormglass data available yet. Submit a prediction first.");
        return;
    }

    const coords = lastPrediction.stormglass_coords;
    document.getElementById("lat").value = coords.lat;
    document.getElementById("lon").value = coords.lon;
});

document.getElementById("save-dive-btn").addEventListener("click", () => {
    if (!lastPrediction) return alert("Make a prediction first.");

    const payload = {
        lat: lastPrediction.stormglass_coords.lat,
        lon: lastPrediction.stormglass_coords.lon,
        visibility: lastPrediction.visibility_m,
        notes: prompt("Add notes for this dive (optional):")
    };

    fetch("/save_dive", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload)
    }).then(() => {
        alert("Dive saved!");
    });
});


// Handle prediction with conversion of numeric fields
document.getElementById("form").addEventListener("submit", async function (e) {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.target).entries());
    
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