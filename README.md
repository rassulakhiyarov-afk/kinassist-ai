# KinAssist AI: Voice Companion for Seniors 👵🎙️

> **Hackathon:** All Things Agentic Hackathon (Organizer: Google LLC, Administrator: Devpost)  
> **Target Track:** The Collaborative Partner  
> **Submission Deadline:** August 31, 2026, 17:00 PT  
> **Target Audience:** Elderly users (70+ years old) and their family caregivers/relatives.

---

## 1. Executive Summary & Vision

**KinAssist AI** is a real-time, bidirectional voice companion engineered specifically for senior citizens aged 70 and older. Built on **Google Gemini 2.5 Flash / Live API** and deployed on **Google Cloud Platform (Vertex AI & Cloud Run)**, KinAssist provides an empathetic, endlessly patient companion capable of effortless natural conversations, jargon-free technical troubleshooting, memory & schedule tracking, and autonomous emergency sentinel protection.

---

## 2. System Architecture & Tech Stack

```
   ┌─────────────────────────────────────────────────────────────┐
   │         Mobile-First Senior Frontend (index.html)           │
   │  • Web Audio API (16kHz PCM Streaming & 24kHz Mono Player)  │
   │  • Large-Target Accessibility UI (Max-width: 430px)         │
   │  • High-Contrast Mode & Real-time Live Subtitles            │
   └──────────────────────────────▲──────────────────────────────┘
                                  │ Bidirectional WebSockets
                                  │ (Raw PCM Audio & Events)
                                  ▼
   ┌─────────────────────────────────────────────────────────────┐
   │             FastAPI Streaming Bridge (main.py)              │
   │  • Python 3.11+ / Uvicorn Server on Cloud Run (Port 8080)   │
   │  • Dual-channel Upstream & Downstream Async Event Loops     │
   │  • Acoustic Echo Suppression & Soft-Mute Barge-in Handling  │
   └──────────────┬───────────────────────────────┬──────────────┘
                  │                               │
       Google GenAI SDK v2                        │ Non-blocking async tasks
  (vertexai=True, us-central1)                    │ (asyncio.create_task)
                  │                               │
                  ▼                               ▼
   ┌─────────────────────────────┐  ┌────────────────────────────┐
   │      Google Gemini Live     │  │   Google Cloud Firestore   │
   │      (Gemini 2.5 Flash)     │  │   (kinassist_logs)         │
   │ • Native Audio Streaming    │  │ • Tech Support Logs        │
   │ • Multilingual Voice (Aoede)│  │ • Daily Tasks & Routines   │
   │ • Server-Side VAD & Tools   │  │ • Urgent Sentinel Alerts   │
   └─────────────────────────────┘  └────────────────────────────┘
```

### Core Technologies:
* **AI Model:** Gemini 2.5 Flash / Live API (`gemini-live-2.5-flash-native-audio`) for low-latency full-duplex speech.
* **GCP Billing & Compute:** Google Vertex AI (`vertexai=True`, `project=PROJECT_ID`, `location="us-central1"`) consuming GCP hackathon credits.
* **Agent Framework:** Google GenAI SDK v2 / Antigravity ADK for real-time agentic tool invocation and unblocking.
* **Backend:** Python 3.11+ / FastAPI / Uvicorn with WebSockets (`/ws/live`).
* **Database & Persistence:** Google Cloud Firestore (`kinassist_logs` collection for structured event persistence).
* **Frontend:** Mobile-first single-screen web application (`index.html`) optimized for touch and senior accessibility.
* **Serverless Hosting:** Google Cloud Run with WebSocket streaming and session affinity.

---

## 3. Agentic Routing (3 Autonomous Scenarios)

KinAssist AI dynamically detects user intent during conversation and routes to 3 autonomous tools without interrupting the voice flow:

### 🛠️ Action A: Tech Support & Device Guidance (Jargon-Free)
* **Rule:** If the senior asks for help with a phone, tablet, TV, or appliance, the assistant breaks instructions into a **maximum of 3 numbered steps** without IT jargon (no words like *cache*, *router*, *reboot*, *browser*, *SSID*, *URL*).
* **Tool Invocation:** `tool_log_tech_support`
* **Firestore Schema:**
  ```json
  {
    "category": "tech_support",
    "device_or_app": "TV Remote",
    "issue_description": "Cannot find favorite channel",
    "steps_provided": "1. Press green power button. 2. Press large 3 button.",
    "resolved": true,
    "created_at": "2026-08-30T12:00:00Z"
  }
  ```

### 📅 Action B: Companion Tasks & Schedules
* **Rule:** When the senior mentions appointments, medications, grocery items, or memories, KinAssist listens with deep empathy and structured persistence.
* **Tool Invocation:** `tool_log_companion_task`
* **Firestore Schema:**
  ```json
  {
    "category": "companion_task",
    "task_type": "medication",
    "description": "Take blue blood pressure pill after lunch",
    "scheduled_time": "1:30 PM",
    "created_at": "2026-08-30T12:00:00Z"
  }
  ```

### 🚨 Action C: Urgent Sentinel & Wellness Alerts
* **Rule:** If the senior reports distress, pain, dizziness, falls, fear (*"I'm scared"*), or activates the emergency button, the assistant immediately provides calming reassurance in their language and flags the log as `status: "URGENT"`.
* **Tool Invocation:** `tool_trigger_urgent_alert`
* **Firestore Schema:**
  ```json
  {
    "category": "urgent_alert",
    "emergency_type": "Senior distress / pain",
    "details": "Felt sudden dizziness in kitchen",
    "severity": "CRITICAL",
    "status": "URGENT",
    "created_at": "2026-08-30T12:00:00Z"
  }
  ```

---

## 4. Minimalist Repository Structure

```
kinassist-ai/
├── main.py              # FastAPI server, WebSocket bridge, Vertex AI Live API & Firestore logging
├── index.html           # Minimalist mobile-first frontend with Web Audio API & Senior UI
├── requirements.txt     # Python runtime dependencies
├── Dockerfile           # Production container definition for Google Cloud Run
└── README.md            # Hackathon project documentation
```

---

## 5. Local & Cloud Shell Execution

### 1. Install Dependencies:
```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables:
```bash
export GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
export GOOGLE_CLOUD_LOCATION="us-central1"
export LIVE_MODEL="gemini-live-2.5-flash-native-audio"
# Optional API Key fallback for local AI Studio development:
export GEMINI_API_KEY="your-gemini-api-key"
```

### 3. Run FastAPI with Streaming WebSockets:
```bash
python3 -m uvicorn main:app --host 0.0.0.0 --port 8080 --ws websockets --timeout-keep-alive 300
```

Access the interface in your browser at `http://localhost:8080`.

---

## 6. Google Cloud Run Deployment

Deploy seamlessly to Cloud Run with full WebSocket and session affinity support:

```bash
gcloud run deploy kinassist-ai \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --timeout 3600 \
  --session-affinity \
  --set-env-vars GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT,GOOGLE_CLOUD_LOCATION=us-central1
```

---

## 7. REST Endpoints

* `GET /` — Serves senior voice interface (`index.html`)
* `GET /healthz` — System health check for Cloud Run load balancer
* `GET /api/logs` — Real-time Firestore logs query endpoint for caregivers & judges
* `WS /ws/live` — Bi-directional full-duplex PCM audio streaming & agentic tool communication
