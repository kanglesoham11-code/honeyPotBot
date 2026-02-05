// --- INIT MAP (Leaflet.js) ---
const map = L.map('map').setView([20, 0], 2); // Start zoomed out
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; OpenStreetMap &copy; CARTO',
    subdomains: 'abcd',
    maxZoom: 19
}).addTo(map);

let scammerMarker = null;

// --- DOM ELEMENTS ---
const form = document.getElementById("scammer-form");
const input = document.getElementById("message-input");
const chatBox = document.getElementById("chat-box");
const riskScoreDisplay = document.getElementById("risk-score");
const riskRing = document.getElementById("risk-ring");
const extractedList = document.getElementById("extracted-info");
const mapOverlay = document.getElementById("map-overlay");
const voiceToggleBtn = document.getElementById("voice-toggle");
const exportBtn = document.getElementById("export-btn");
const clockDisplay = document.getElementById("clock");

// --- STATE ---
let voiceEnabled = false;

// --- CLOCK ---
setInterval(() => {
    clockDisplay.innerText = new Date().toISOString().split('T')[1].split('.')[0] + " UTC";
}, 1000);

// --- VOICE TOGGLE ---
voiceToggleBtn.addEventListener("click", () => {
    voiceEnabled = !voiceEnabled;
    voiceToggleBtn.innerHTML = voiceEnabled ? '<i class="fa-solid fa-volume-high"></i> VOICE: ON' : '<i class="fa-solid fa-volume-xmark"></i> VOICE: OFF';
    voiceToggleBtn.style.color = voiceEnabled ? "var(--neon-green)" : "var(--neon-cyan)";
});

// --- EXPORT BUTTON (FEATURE 4) ---
exportBtn.addEventListener("click", () => {
    window.location.href = "/api/export_report";
    addMessage("SYSTEM", "DOWNLOADING CASE EVIDENCE FILE...", "system-msg");
});

// --- MAIN LOGIC ---
form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;

    input.value = "";
    addMessage("SCAMMER", text, "scammer");
    showThinking();

    try {
        const res = await fetch("/api/honeypot", {
            method: "POST",
            body: JSON.stringify({ scammer_id: "demo", message: text })
        });
        const data = await res.json();
        
        removeThinking();
        
        // 1. Agent Reply (Type + Speak)
        addMessage("AGENT", data.reply, "agent");
        if (voiceEnabled) speak(data.reply);

        // 2. Update UI
        updateRisk(data.risk);
        updateIntel(data.extracted);
        
        // 3. Update Map (The "Predator" Feature)
        if (data.scammer_intel) {
            updateMap(data.scammer_intel);
        }

    } catch (err) {
        removeThinking();
        console.error(err);
        addMessage("SYSTEM", "NETWORK ERROR", "system-msg");
    }
});

function updateMap(intel) {
    const coords = intel.coords; // [lat, lng]
    
    // Zoom in animation
    map.flyTo(coords, 10, { duration: 3 });

    // Add/Move Marker
    if (scammerMarker) map.removeLayer(scammerMarker);
    
    // Custom Icon
    const customIcon = L.divIcon({
        className: 'custom-pin',
        html: `<div style="background-color:var(--neon-red);width:15px;height:15px;border-radius:50%;box-shadow:0 0 10px var(--neon-red);"></div>`
    });

    scammerMarker = L.marker(coords, {icon: customIcon}).addTo(map)
        .bindPopup(`<b>DETECTED:</b> ${intel.location}<br><b>ISP:</b> ${intel.isp}<br><b>IP:</b> ${intel.ip}`).openPopup();

    mapOverlay.innerHTML = `LOCKED ON: ${intel.location.toUpperCase()} // IP: ${intel.ip}`;
}

function speak(text) {
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.9;
    utterance.pitch = 1.1; // Slightly higher/older sounding
    window.speechSynthesis.speak(utterance);
}

function addMessage(sender, text, type) {
    const div = document.createElement("div");
    div.className = `message ${type}`;
    div.innerHTML = `<strong>${sender}</strong><br>${text}`;
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
    
    // GSAP Pop-in
    gsap.fromTo(div, {opacity: 0, scale: 0.9}, {opacity: 1, scale: 1, duration: 0.3});
}

function updateRisk(val) {
    gsap.to(riskScoreDisplay, { innerText: val, duration: 1, snap: { innerText: 1 } });
    const offset = 283 - (283 * val) / 100;
    riskRing.style.strokeDashoffset = offset;
    riskRing.style.stroke = val > 70 ? "var(--neon-red)" : (val > 40 ? "var(--neon-yellow)" : "var(--neon-green)");
}

function updateIntel(items) {
    if (!items) return;
    extractedList.innerHTML = ""; // Refresh list
    items.forEach(i => {
        const li = document.createElement("li");
        li.innerText = i;
        extractedList.appendChild(li);
    });
}

function showThinking() {
    const div = document.createElement("div");
    div.id = "thinking-loader";
    div.className = "system-msg";
    div.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> ANALYZING...`;
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function removeThinking() {
    const el = document.getElementById("thinking-loader");
    if(el) el.remove();
}