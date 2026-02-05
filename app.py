from flask import Flask, request, jsonify, render_template, Response
from flask_cors import CORS
from dotenv import load_dotenv
import os, sqlite3, uuid, json, time, random
from datetime import datetime, timezone
from groq import Groq
from faker import Faker

# --------------------
# ⚙️ CONFIG
# --------------------
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise RuntimeError("❌ GROQ_API_KEY not found in .env")

app = Flask(__name__)
CORS(app)

client = Groq(api_key=GROQ_API_KEY)
fake = Faker()

DB_FILE = "honeypot.db"

# --------------------
# 🗄️ DATABASE
# --------------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            start_time REAL,
            scammer_ip TEXT,
            scammer_loc TEXT,
            scammer_lat REAL,
            scammer_lng REAL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            session_id TEXT,
            timestamp TEXT,
            sender TEXT,
            content TEXT,
            psychology TEXT,
            strategy TEXT,
            fake_data_leaked TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# --------------------
# 🧠 INTELLIGENCE ENGINE
# --------------------
def generate_fake_data(info_type):
    """Generates realistic fake data for the honey trap."""
    if "card" in info_type or "bank" in info_type:
        return f"Visa: {fake.credit_card_number(card_type='visa')}, CVV: {fake.credit_card_security_code()}"
    elif "name" in info_type:
        return f"Name: {fake.name()}"
    elif "address" in info_type:
        return f"Address: {fake.address().replace(chr(10), ', ')}"
    elif "email" in info_type:
        return f"Email: {fake.email()}"
    return "..."

def get_scammer_profile():
    """Simulates a 'Dark Web' lookup of the scammer."""
    locations = [
        {"city": "Lagos, Nigeria", "lat": 6.5244, "lng": 3.3792},
        {"city": "Moscow, Russia", "lat": 55.7558, "lng": 37.6173},
        {"city": "Kolkata, India", "lat": 22.5726, "lng": 88.3639},
        {"city": "Manila, Philippines", "lat": 14.5995, "lng": 120.9842},
        {"city": "New York, USA", "lat": 40.7128, "lng": -74.0060},
        {"city": "Bucharest, Romania", "lat": 44.4268, "lng": 26.1025}
    ]
    loc = random.choice(locations)
    return {
        "ip": fake.ipv4(),
        "isp": fake.company() + " Networks",
        "location": loc["city"],
        "coords": [loc["lat"], loc["lng"]],
        "device": random.choice(["Android 14", "Windows 11 PC", "Unknown Linux Distro"]),
        "vpn_detected": random.choice([True, False])
    }

def analyze_and_reply(message, history):
    system_prompt = f"""
    You are an advanced Cyber-Counterintelligence Agent acting as a 'Honey Pot'.
    
    YOUR PERSONA:
    You are a polite, slightly confused elderly person who is not tech-savvy. 
    You are interested in what the scammer is offering but you are cautious.
    
    RULES:
    1. WRITE PERFECT ENGLISH. No fake typos. Be professional but naive.
    2. BE NAIVE: Misunderstand technical terms (e.g., confuse 'Bitcoin' with 'Bit-coin tokens').
    3. GOAL: Keep them talking as long as possible.
    
    TASK:
    1. ANALYZE: Determine the scammer's 'Psychology' (e.g., Aggressive, Desperate) and 'Strategy'.
    2. TRAP: If they ask for personal info (Bank, Name, Email), output a placeholder like [GENERATE_CARD] or [GENERATE_NAME].
    3. REPLY: Generate the response based on the Persona.

    OUTPUT FORMAT (JSON ONLY):
    {{
        "psychology": "Analysis of their mood",
        "strategy": "What scam tactic they are using",
        "reply": "Your message to them",
        "trigger_trap": "null" or "card/name/address/bank"
    }}
    
    Conversation History:
    {history}
    """
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": message}],
            temperature=0.6,
            response_format={"type": "json_object"}
        )
        return json.loads(completion.choices[0].message.content)
    except Exception as e:
        print(f"❌ LLM Error: {e}")
        return {"psychology": "Unknown", "strategy": "General", "reply": "I'm sorry, my computer is acting up. Could you say that again?", "trigger_trap": None}

# --------------------
# 🚀 ROUTES
# --------------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/honeypot", methods=["POST"])
def honeypot():
    data = request.get_json(force=True)
    scammer_msg = data.get("message", "").strip()
    session_id = data.get("scammer_id", "demo")

    # 1. Simulate finding the scammer (Geo-Trace)
    scammer_intel = get_scammer_profile()

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # Time tracking & Session Init
    cur.execute("SELECT start_time FROM sessions WHERE session_id=?", (session_id,))
    row = cur.fetchone()
    if not row:
        start_time = time.time()
        cur.execute("INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?)", 
                    (session_id, start_time, scammer_intel['ip'], scammer_intel['location'], scammer_intel['coords'][0], scammer_intel['coords'][1]))
    else:
        start_time = row[0]
    time_wasted = int(time.time() - start_time)

    # History
    cur.execute("SELECT sender, content FROM messages WHERE session_id=? ORDER BY timestamp DESC LIMIT 5", (session_id,))
    rows = cur.fetchall()[::-1]
    history = "\n".join([f"{r[0]}: {r[1]}" for r in rows])

    # 2. AI Logic
    ai_data = analyze_and_reply(scammer_msg, history)
    reply = ai_data.get("reply")
    fake_leak = None
    
    # Honey Trap Injection
    trap = ai_data.get("trigger_trap")
    if trap and trap not in ["null", "None"]:
        fake_info = generate_fake_data(trap)
        if "[GENERATE" in reply:
            reply = reply.replace("[GENERATE_CARD]", fake_info).replace("[GENERATE_NAME]", fake_info).replace("[GENERATE_DATA]", fake_info)
        else:
            reply += f" {fake_info}"
        fake_leak = fake_info

    # Save
    ts = datetime.now(timezone.utc).isoformat()
    cur.execute("INSERT INTO messages VALUES (?,?,?,?,?,?,?,?)", (str(uuid.uuid4()), session_id, ts, "Scammer", scammer_msg, ai_data.get('psychology'), ai_data.get('strategy'), None))
    cur.execute("INSERT INTO messages VALUES (?,?,?,?,?,?,?,?)", (str(uuid.uuid4()), session_id, ts, "Agent", reply, None, None, fake_leak))
    conn.commit()
    conn.close()

    # 3. Response Construction
    return jsonify({
        "reply": reply,
        "risk": 99 if fake_leak else random.randint(40, 90),
        "extracted": [
            f"Psychology: {ai_data.get('psychology')}",
            f"Strategy: {ai_data.get('strategy')}",
            f"⏱️ Wasted: {time_wasted}s"
        ],
        "scammer_intel": scammer_intel # Feature: Send coordinates to frontend
    })

@app.route("/api/export_report")
def export_report():
    session_id = "demo"
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute("SELECT scammer_ip, scammer_loc, start_time FROM sessions WHERE session_id=?", (session_id,))
    session_data = cur.fetchone()
    
    if not session_data:
        return jsonify({"error": "No active session found"}), 404

    ip, loc, start_time = session_data
    formatted_time = datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S UTC')

    cur.execute("SELECT timestamp, sender, content, psychology, strategy FROM messages WHERE session_id=? ORDER BY timestamp ASC", (session_id,))
    logs = cur.fetchall()
    conn.close()

    report = []
    report.append("==================================================")
    report.append("       CONFIDENTIAL // CYBER-CRIME EVIDENCE LOG")
    report.append("==================================================")
    report.append(f"CASE ID:      {str(uuid.uuid4())[:8].upper()}")
    report.append(f"DATE:         {datetime.now().strftime('%Y-%m-%d')}")
    report.append(f"STATUS:       ACTIVE INTERCEPTION")
    report.append("--------------------------------------------------")
    report.append("TARGET INTELLIGENCE:")
    report.append(f"[*] IP ADDRESS:   {ip}")
    report.append(f"[*] GEO-LOCATION: {loc}")
    report.append(f"[*] FIRST SEEN:   {formatted_time}")
    report.append("==================================================\n")
    report.append("TRANSCRIPT LOG:")
    
    for row in logs:
        ts, sender, content, psych, strategy = row
        clean_ts = ts.split("T")[1][:8] 
        report.append(f"[{clean_ts}] {sender.upper()}: {content}")
        if sender == "Scammer" and psych:
            report.append(f"      >>> ANALYST NOTE: Target appears {psych}. Tactic: {strategy}.")
        report.append("")

    report.append("\n==================================================")
    report.append("END OF REPORT // AUTOMATED GENERATION")
    report.append("==================================================")
    
    return Response(
        "\n".join(report),
        mimetype="text/plain",
        headers={"Content-Disposition": "attachment;filename=case_evidence_log.txt"}
    )

if __name__ == "__main__":
    app.run(debug=True, port=5000)