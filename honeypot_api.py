from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from typing import Dict
import time
import re
import requests
import json
app = FastAPI(title="Agentic Honeypot – Scam Detection System")
#configure
API_KEY = "my-secret-honeypot-key"  
GUVI_CALLBACK_URL = "https://hackathon.guvi.in/api/updateHoneyPotFinalResult"
SCAM_KEYWORDS = [
    "urgent", "verify", "account blocked", "kyc",
    "upi", "bank", "click", "link", "suspend"
]
SESSIONS = {}
#helpers
def detect_scam(text: str):
    hits = [k for k in SCAM_KEYWORDS if k in text.lower()]
    return len(hits) >= 2, hits
def extract_intelligence(text: str, intel: Dict):
    intel["upiIds"] += re.findall(r"[a-zA-Z0-9.\-_]{2,}@[a-zA-Z]{2,}", text)
    intel["bankAccounts"] += re.findall(r"\b\d{9,18}\b", text)
    intel["phishingLinks"] += re.findall(r"https?://\S+", text)
    intel["phoneNumbers"] += re.findall(r"\+91\d{10}", text)
def agent_response(session):
    msgs = [m["text"].lower() for m in session["messages"] if m["sender"] == "scammer"]
    recent = msgs[-2:] if len(msgs) >= 2 else msgs
    if sum("urgent" in m or "verify" in m for m in recent) >= 2:
        return "You already said it is urgent. I’m confused and worried. Can you explain slowly?"
    if any("http" in m for m in recent):
        return "I don’t usually click links. What exactly will happen if I open it?"
    if len(session["messages"]) > 4:
        return "This is a lot of information. What should I do first?"
    return "I’m not very technical. Please guide me step by step."
def send_guvi_callback(session_id, session):
    payload = {
        "sessionId": session_id,
        "scamDetected": True,
        "totalMessagesExchanged": len(session["messages"]),
        "extractedIntelligence": session["intel"],
        "agentNotes": "Urgency pressure and redirection tactics observed"
    }
    try:
        requests.post(GUVI_CALLBACK_URL, json=payload, timeout=5)
    except:
        pass
#API
@app.post("/honeypot")
def honeypot(payload: Dict, x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    session_id = payload["sessionId"]
    message = payload["message"]
    history = payload.get("conversationHistory", [])
    if session_id not in SESSIONS:
        SESSIONS[session_id] = {
            "start": time.time(),
            "messages": [],
            "scamDetected": False,
            "callbackSent": False,
            "intel": {
                "bankAccounts": [],
                "upiIds": [],
                "phishingLinks": [],
                "phoneNumbers": [],
                "suspiciousKeywords": []
            }
        }
    session = SESSIONS[session_id]
    for h in history:
        session["messages"].append(h)
    session["messages"].append(message)
    is_scam, keywords = detect_scam(message["text"])
    if is_scam:
        session["scamDetected"] = True
        session["intel"]["suspiciousKeywords"] += keywords
    extract_intelligence(message["text"], session["intel"])
    reply = None
    if session["scamDetected"]:
        reply = agent_response(session)
    if session["scamDetected"] and len(session["messages"]) >= 6 and not session["callbackSent"]:
        send_guvi_callback(session_id, session)
        session["callbackSent"] = True
    return JSONResponse({
        "status": "success",
        "scamDetected": session["scamDetected"],
        "agentResponse": reply,
        "engagementMetrics": {
            "engagementDurationSeconds": int(time.time() - session["start"]),
            "totalMessagesExchanged": len(session["messages"])
        },
        "extractedIntelligence": session["intel"],
        "agentNotes": "Scammer used urgency tactics and payment redirection"
    })
#UI
@app.get("/", response_class=HTMLResponse)
def dashboard():
    return """
<!DOCTYPE html>
<html>
<head>
  <title>Agentic Honeypot Dashboard</title>
  <style>
    body { font-family: Arial; background: #f3f4f6; padding: 40px; }
    h1 { color: #111827; }
    .card { background: white; padding: 20px; border-radius: 10px;
            margin-bottom: 20px; box-shadow: 0 2px 6px rgba(0,0,0,.1); }
    textarea, input { width: 100%; padding: 10px; margin-top: 8px; }
    button { padding: 10px 20px; background: #2563eb; color: white;
             border: none; border-radius: 5px; cursor: pointer; }
    pre { background: #e5e7eb; padding: 10px; }
    .error { color: red; }
  </style>
</head>
<body>
<h1>🛡️ Agentic Honeypot System</h1>
<div class="card">
  <h3>API Key</h3>
  <input id="apiKey" placeholder="Enter x-api-key" />
</div>
<div class="card">
  <h3>Test Honeypot API</h3>
  <textarea id="jsonInput">
{
  "sessionId": "test-001",
  "message": {
    "sender": "scammer",
    "text": "Your bank account will be blocked today. Verify urgently.",
    "timestamp": "2026-01-21T10:15:30Z"
  },
  "conversationHistory": []
}
  </textarea>
  <br><br>
  <button onclick="send()">Send</button>
</div>
<div class="card">
  <h3>Response</h3>
  <pre id="output"></pre>
</div>
<script>
function send() {
  const key = document.getElementById("apiKey").value;
  if (!key) {
    document.getElementById("output").textContent = "❌ API key is required";
    return;
  }
  fetch("/honeypot", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": key
    },
    body: document.getElementById("jsonInput").value
  })
  .then(res => res.json())
  .then(data => {
    document.getElementById("output").textContent =
      JSON.stringify(data, null, 2);
  })
  .catch(err => {
    document.getElementById("output").textContent = "❌ Request failed";
  });
}
</script>
</body>
</html>
"""
