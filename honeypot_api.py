from fastapi import FastAPI, Header, HTTPException
from typing import List, Dict, Optional
from datetime import datetime
import re
import os
import requests
#config
API_KEY = os.getenv("API_KEY")
GUVI_CALLBACK_URL = "https://hackathon.guvi.in/api/updateHoneyPotFinalResult"
app = FastAPI(title="Agentic HoneyPot API", version="1.0")
@app.get("/")
def home():
    return {
        "service": "Agentic HoneyPot API",
        "status": "running",
        "docs": "/docs",
        "endpoint": "/honeypot",
        "note": "Use POST /honeypot with JSON body"
    }
#memory store
SESSIONS = {}
#helpers
SCAM_KEYWORDS = [
    "urgent", "verify", "account blocked", "suspend",
    "upi", "bank", "click", "link", "otp", "immediately"
]
BANK_REGEX = r"\b\d{9,18}\b"
UPI_REGEX = r"\b[\w.-]+@[\w.-]+\b"
URL_REGEX = r"https?://[^\s]+"
PHONE_REGEX = r"\+91\d{10}"
def validate_api_key(x_api_key: str):
    if not API_KEY:
        raise HTTPException(status_code=500, detail="API key not configured")
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
def detect_scam(text: str) -> bool:
    text = text.lower()
    return any(word in text for word in SCAM_KEYWORDS)
def extract_intelligence(text: str, intel: dict):
    intel["bankAccounts"] += re.findall(BANK_REGEX, text)
    intel["upiIds"] += re.findall(UPI_REGEX, text)
    intel["phishingLinks"] += re.findall(URL_REGEX, text)
    intel["phoneNumbers"] += re.findall(PHONE_REGEX, text)
    for word in SCAM_KEYWORDS:
        if word in text.lower() and word not in intel["suspiciousKeywords"]:
            intel["suspiciousKeywords"].append(word)
def agent_reply(turns: int) -> str:
    replies = [
        "I am a bit confused. Can you explain again?",
        "I am worried. What exactly should I do now?",
        "I don’t want my account blocked. Please guide me.",
        "Earlier you said something else. Can you clarify?",
        "I’m trying to follow, please be patient."
    ]
    return replies[turns % len(replies)]
    def send_final_callback(session_id: str, session: dict):
     payload = {
        "sessionId": session_id,
        "scamDetected": True,
        "totalMessagesExchanged": session["totalMessages"],
        "extractedIntelligence": session["intelligence"],
        "agentNotes": "Scammer used urgency and payment redirection tactics"
    }

    try:
        requests.post(
            "https://hackathon.guvi.in/api/updateHoneyPotFinalResult",
            json=payload,
            timeout=5
        )
        print("✅ GUVI callback sent successfully for session:", session_id)
    except Exception as e:
        print("❌ GUVI callback failed for session:", session_id, "Error:", e)

#api endpoint
@app.post("/honeypot")
def honeypot(
    body: Dict,
    x_api_key: Optional[str] = Header(None)
):
    validate_api_key(x_api_key)

    session_id = body["sessionId"]
    message = body["message"]["text"]
    history = body.get("conversationHistory", [])
    if session_id not in SESSIONS:
        SESSIONS[session_id] = {
            "scamDetected": False,
            "totalMessages": 0,
            "intelligence": {
                "bankAccounts": [],
                "upiIds": [],
                "phishingLinks": [],
                "phoneNumbers": [],
                "suspiciousKeywords": []
            }
        }
    session = SESSIONS[session_id]
    session["totalMessages"] += 1
    #Detectscam
    if not session["scamDetected"] and detect_scam(message):
        session["scamDetected"] = True
     #If scam detected engage agent
    agent_response = None
    if session["scamDetected"]:
        extract_intelligence(message, session["intelligence"])
        agent_response = agent_reply(session["totalMessages"])
       #End engagement after enough turns
        if session["totalMessages"] >= 8:
            send_final_callback(session_id, session)
    return {
        "status": "success",
        "scamDetected": session["scamDetected"],
        "agentReply": agent_response,
        "engagementMetrics": {
            "totalMessagesExchanged": session["totalMessages"]
        },
        "extractedIntelligence": session["intelligence"],
        "agentNotes": "Scammer used urgency tactics and payment redirection"
    }
