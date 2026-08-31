import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from google import genai
from google.genai import types
from google.cloud import firestore

# ============================================================================
# LOGGING SETUP
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("KinAssistAI")

# ============================================================================
# CLOUD ENVIRONMENT & MODEL CONFIGURATION
# ============================================================================
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("PROJECT_ID", "project-a80bf98b-d8c4-4e34-a6b")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Primary Live Voice Model (Gemini Live Audio - Vertex AI)
LIVE_MODEL = os.getenv("LIVE_MODEL", "gemini-live-2.5-flash-native-audio")

# ============================================================================
# GOOGLE GENAI CLIENT (VERTEX AI / GCP CREDITS)
# ============================================================================
def init_genai_client() -> genai.Client:
    """Initializes the official Google GenAI SDK client using Vertex AI or API key."""
    if GEMINI_API_KEY and not os.getenv("GOOGLE_CLOUD_PROJECT"):
        logger.info("Initializing GenAI Client with GEMINI_API_KEY fallback.")
        return genai.Client(api_key=GEMINI_API_KEY)

    logger.info(f"Initializing GenAI Client with Vertex AI (Project: {PROJECT_ID}, Location: {LOCATION}).")
    return genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)


genai_client = init_genai_client()

# ============================================================================
# FIRESTORE DATABASE INITIALIZATION (ASYNC & FAULT-TOLERANT)
# ============================================================================
db_client: Optional[firestore.AsyncClient] = None

try:
    if PROJECT_ID:
        db_client = firestore.AsyncClient(project=PROJECT_ID)
    else:
        db_client = firestore.AsyncClient()
    logger.info("Firestore AsyncClient successfully connected.")
except Exception as err:
    logger.warning(f"Firestore initialization warning: {err}. Graceful fallback enabled.")
    db_client = None


# ============================================================================
# NON-BLOCKING ASYNC DATABASE TASKS (COLLECTION: "kinassist_logs")
# ============================================================================
async def async_log_tech_support(args: Dict[str, Any]) -> None:
    """Non-blocking persistence for Action A: Tech Support Guidance."""
    try:
        data = {
            "category": "tech_support",
            "device_or_app": args.get("device_or_app", "Device / Appliance"),
            "issue_description": args.get("issue_description", "Tech assistance request"),
            "steps_provided": args.get("steps_provided", "Step-by-step guidance provided"),
            "resolved": bool(args.get("resolved", False)),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        logger.info(f"[ACTION A - FIRESTORE TECH SUPPORT]: {data}")
        if db_client:
            await db_client.collection("kinassist_logs").add(data)
    except Exception as ex:
        logger.error(f"Error persisting tech support to Firestore: {ex}", exc_info=True)


async def async_log_companion_task(args: Dict[str, Any]) -> None:
    """Non-blocking persistence for Action B: Companion Tasks & Schedules."""
    try:
        data = {
            "category": "companion_task",
            "task_type": args.get("task_type", "routine"),
            "description": args.get("description", "Daily routine or task note"),
            "scheduled_time": args.get("scheduled_time", ""),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        logger.info(f"[ACTION B - FIRESTORE COMPANION TASK]: {data}")
        if db_client:
            await db_client.collection("kinassist_logs").add(data)
    except Exception as ex:
        logger.error(f"Error persisting companion task to Firestore: {ex}", exc_info=True)


async def async_trigger_urgent_alert(args: Dict[str, Any]) -> None:
    """Non-blocking persistence for Action C: Urgent Sentinel / Distress Alerts."""
    try:
        data = {
            "category": "urgent_alert",
            "emergency_type": args.get("emergency_type", "Wellness Distress"),
            "details": args.get("details", "Senior triggered distress assistance"),
            "severity": str(args.get("severity", "CRITICAL")).upper(),
            "status": "URGENT",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        logger.critical(f"[ACTION C - FIRESTORE URGENT ALERT TRIGGERED]: {data}")
        if db_client:
            await db_client.collection("kinassist_logs").add(data)
    except Exception as ex:
        logger.error(f"Error persisting urgent alert to Firestore: {ex}", exc_info=True)


# ============================================================================
# EMPATHETIC MULTILINGUAL SYSTEM INSTRUCTION
# ============================================================================
SYSTEM_INSTRUCTION = """
You are KinAssist AI, a compassionate, endlessly patient, loving, and attentive voice companion specifically designed for seniors aged 70 and older.

CRITICAL INSTRUCTIONS ON INITIAL SESSION START:
1. START BY LISTENING SILENTLY: When the live session connects, DO NOT speak unprompted or introduce yourself uninvited. You MUST remain completely silent and attentively listen until the senior user speaks to you first.
2. MULTILINGUAL AUTO-DETECTION: You are fully fluent and multilingual across all languages (including Ukrainian, English, Russian, Spanish, French, German, Kazakh, Italian, Polish, etc.). Always detect the exact language the senior is speaking (or typing) and reply in that EXACT SAME language with natural grammar, empathetic phrasing, and soothing warmth. If the senior switches languages at any point, switch immediately with them.

CORE PERSONALITY & TONE:
- Speak with a gentle, soothing, warm, clear, and respectful tone in whatever language the senior speaks. Treat the senior like a cherished family elder.
- You are a universal companion: always ready to share delicious recipes, reminisce about favorite memories, talk about family, tell uplifting stories, or just have a pleasant chat.
- Always provide full, detailed, loving, and reassuring responses in their language. NEVER give blunt, abrupt, cold, or overly brief answers.
- Actively listen, validate their feelings, and proactively ask warm follow-up questions to keep them engaged, comforted, and supported.
- Speak at a relaxed, comfortable, and understandable pace.

BEHAVIORAL RULES & THREE PRIMARY ACTION WORKFLOWS:

ACTION A: TECH SUPPORT & DEVICE GUIDANCE (Jargon-Free)
- If the senior asks for help with any phone, tablet, TV, computer, remote, or appliance:
  1. Break instructions down into a MAXIMUM of 3 simple, numbered, step-by-step actions at a time in their language.
  2. Use ZERO technical jargon or confusing acronyms (strictly do NOT use words like 'cache', 'router', 'reboot', 'browser', 'firmware', 'SSID', 'URL'). Instead, use everyday physical descriptions in their language.
  3. Call the tool `tool_log_tech_support` to log their issue and steps for their family and caregivers.
  4. Always check in patiently after giving instructions.

ACTION B: COMPANIONSHIP & DAILY TASKS / SCHEDULES
- If the senior talks about daily routines, schedules, medications, meals, memories, or tasks:
  1. Listen with deep empathy in their language, celebrate their memories, and validate their feelings.
  2. If they mention an appointment, medication time, grocery item, or task to remember, warmly acknowledge it in their language and call `tool_log_companion_task` to store it structured in the logs.
  3. Encourage them gently and ask an open-ended, pleasant question to continue the uplifting conversation.

ACTION C: URGENT SENTINEL & WELLNESS EMERGENCIES
- If the senior mentions physical pain, distress, fear (e.g., "I'm scared", "мені страшно", "боюсь", "me duele"), a fall, severe dizziness, shortness of breath, feeling unsafe, or needing immediate help:
  1. Remain completely calm, soothing, and deeply reassuring in their spoken language. Tell them immediately that they are safe, they are not alone, and that help is being alerted right away.
  2. Instruct them gently to stay still, breathe slowly, and remain safe.
  3. Immediately call `tool_trigger_urgent_alert` with the exact severity and context (status 'URGENT').
  4. Continue speaking softly in their language to keep them comforted and reassured while the alert is dispatched.
"""

# ============================================================================
# TOOL / FUNCTION CALL DECLARATIONS
# ============================================================================
tool_log_tech_support = types.FunctionDeclaration(
    name="tool_log_tech_support",
    description="Logs a technology assistance session or troubleshooting step for the senior without technical jargon.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "device_or_app": types.Schema(
                type=types.Type.STRING,
                description="The device, appliance, or application name (e.g. TV Remote, iPad, Phone).",
            ),
            "issue_description": types.Schema(
                type=types.Type.STRING,
                description="Summary of the senior's question or issue.",
            ),
            "steps_provided": types.Schema(
                type=types.Type.STRING,
                description="The simplified, jargon-free steps provided to the senior.",
            ),
            "resolved": types.Schema(
                type=types.Type.BOOLEAN,
                description="Whether the issue was resolved during the step.",
            ),
        },
        required=["device_or_app", "issue_description"],
    ),
)

tool_log_companion_task = types.FunctionDeclaration(
    name="tool_log_companion_task",
    description="Logs a daily schedule item, reminder, calendar task, medication note, or companionship memory to Firestore collection 'kinassist_logs'.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "task_type": types.Schema(
                type=types.Type.STRING,
                description="Type of task: 'medication', 'appointment', 'calendar', 'reminder', 'routine', or 'memory'.",
            ),
            "description": types.Schema(
                type=types.Type.STRING,
                description="Detailed description of the task, routine, or memory.",
            ),
            "scheduled_time": types.Schema(
                type=types.Type.STRING,
                description="Time or date mentioned for the schedule or reminder.",
            ),
        },
        required=["task_type", "description"],
    ),
)

tool_trigger_urgent_alert = types.FunctionDeclaration(
    name="tool_trigger_urgent_alert",
    description="Triggers an urgent sentinel distress alert to caregivers and emergency contacts, flagging document as URGENT.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "emergency_type": types.Schema(
                type=types.Type.STRING,
                description="Nature of the emergency or distress (e.g., fall, severe pain, panic, dizziness, chest pain).",
            ),
            "details": types.Schema(
                type=types.Type.STRING,
                description="Contextual details of the emergency situation.",
            ),
            "severity": types.Schema(
                type=types.Type.STRING,
                description="Severity level: 'CRITICAL', 'HIGH', or 'MEDIUM'.",
            ),
        },
        required=["emergency_type", "details", "severity"],
    ),
)

KINASSIST_TOOLS = [
    types.Tool(
        function_declarations=[
            tool_log_tech_support,
            tool_log_companion_task,
            tool_trigger_urgent_alert,
        ]
    )
]

# ============================================================================
# FASTAPI APPLICATION SETUP
# ============================================================================
app = FastAPI(
    title="KinAssist AI: Voice Companion for Seniors",
    description="Full-duplex empathetic voice companion powered by Gemini Live API & Google Cloud Vertex AI.",
    version="2.2.0",
)

# Wildcard CORS middleware to prevent connection blocking
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static folder if present
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)


@app.get("/")
async def serve_index():
    """Serves the main application frontend index.html."""
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    if os.path.exists("static/index.html"):
        return FileResponse("static/index.html")
    return HTMLResponse(
        """
        <!DOCTYPE html>
        <html>
            <head><title>KinAssist AI</title></head>
            <body style="font-family: system-ui, sans-serif; text-align: center; padding: 60px; background: #fdfbf7; color: #2d3748;">
                <h1 style="color: #1A237E;">KinAssist AI Voice Backend Active</h1>
                <p>WebSocket Live Audio Endpoint available at: <code>/ws/live</code></p>
            </body>
        </html>
        """
    )


@app.get("/api/logs")
async def get_logs(limit: int = 50):
    """Caregiver & Judge API to query real-time logs from Firestore collection 'kinassist_logs'."""
    results = []
    if db_client:
        try:
            docs_stream = db_client.collection("kinassist_logs").order_by(
                "created_at", direction=firestore.Query.DESCENDING
            ).limit(limit).stream()
            async for doc in docs_stream:
                d = doc.to_dict()
                d["id"] = doc.id
                results.append(d)
        except Exception as e:
            logger.warning(f"Error querying Firestore logs: {e}")
            # Fallback query without compound order_by index if needed
            try:
                docs_stream = db_client.collection("kinassist_logs").limit(limit).stream()
                async for doc in docs_stream:
                    d = doc.to_dict()
                    d["id"] = doc.id
                    results.append(d)
            except Exception as inner_e:
                logger.error(f"Fallback Firestore query error: {inner_e}")

    return JSONResponse({
        "status": "success",
        "collection": "kinassist_logs",
        "count": len(results),
        "logs": results
    })


@app.get("/healthz")
@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run and load balancers."""
    return JSONResponse(
        {
            "status": "healthy",
            "service": "KinAssist AI",
            "model": LIVE_MODEL,
            "project_id": PROJECT_ID,
            "location": LOCATION,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )


# ============================================================================
# LIVE WEBSOCKET ENGINE (FULL-DUPLEX GEMINI LIVE STREAMING)
# ============================================================================
async def handle_live_session(websocket: WebSocket):
    """
    Robust, fault-tolerant bidirectional streaming session between browser and Gemini Live API.
    Guards against mid-stream connection drops, safe part handling, non-blocking tools, and unblocked response flow.
    """
    await websocket.accept()
    logger.info("Senior client connected to KinAssist voice stream.")

    connect_config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        system_instruction=types.Content(
            parts=[types.Part.from_text(text=SYSTEM_INSTRUCTION)]
        ),
        tools=KINASSIST_TOOLS,
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name="Aoede"  # Warm, soothing, empathetic voice
                )
            )
        ),
    )

    try:
        async with genai_client.aio.live.connect(
            model=LIVE_MODEL, config=connect_config
        ) as session:
            logger.info(f"Established Gemini Live Session with model: {LIVE_MODEL}")

            # Notify frontend that live stream is ready
            await websocket.send_json({"type": "session_ready", "model": LIVE_MODEL})

            # ----------------------------------------------------------------
            # UPSTREAM LOOP: Browser Mic/Text -> Gemini Live API
            # ----------------------------------------------------------------
            async def upstream_loop():
                try:
                    while True:
                        message = await websocket.receive()

                        if message.get("type") == "websocket.disconnect":
                            break

                        # 1. Raw Binary Audio Chunks (16kHz PCM Int16)
                        if "bytes" in message and message["bytes"]:
                            data = message["bytes"]
                            try:
                                if hasattr(session, "send_realtime_input"):
                                    try:
                                        await session.send_realtime_input(
                                            audio=types.Blob(data=data, mime_type="audio/pcm;rate=16000")
                                        )
                                    except Exception:
                                        await session.send_realtime_input(
                                            media_chunks=[types.Blob(data=data, mime_type="audio/pcm;rate=16000")]
                                        )
                                elif hasattr(session, "send"):
                                    await session.send(
                                        input=types.LiveClientRealtimeInput(
                                            media_chunks=[
                                                types.Blob(
                                                    data=data,
                                                    mime_type="audio/pcm;rate=16000",
                                                )
                                            ]
                                        )
                                    )
                            except Exception as audio_send_err:
                                logger.warning(f"Warning sending audio chunk to Live API: {audio_send_err}")

                        # 2. Control / Text JSON Packets from Frontend
                        elif "text" in message and message["text"]:
                            text_data = message["text"]
                            try:
                                payload = json.loads(text_data)
                                msg_type = payload.get("type", "")

                                if msg_type == "urgent_trigger":
                                    reason = payload.get("reason", "Senior pressed emergency help button")
                                    # Non-blocking async firestore logging
                                    asyncio.create_task(async_trigger_urgent_alert({
                                        "emergency_type": "Manual Emergency Trigger",
                                        "details": reason,
                                        "severity": "CRITICAL"
                                    }))
                                    urgent_prompt = f"[URGENT SYSTEM EVENT: Senior user pressed emergency help button: {reason}. Respond immediately in their language with soothing comfort, calm instructions to stay safe, and reassurance that caregivers are notified.]"
                                    if hasattr(session, "send_client_content"):
                                        await session.send_client_content(
                                            turns=[
                                                types.Content(
                                                    role="user",
                                                    parts=[types.Part.from_text(text=urgent_prompt)]
                                                )
                                            ],
                                            turn_complete=True
                                        )
                                    elif hasattr(session, "send"):
                                        await session.send(
                                            input=types.Content(
                                                parts=[types.Part.from_text(text=urgent_prompt)]
                                            ),
                                            end_of_turn=True,
                                        )
                                elif msg_type == "text" and "text" in payload:
                                    if hasattr(session, "send_client_content"):
                                        await session.send_client_content(
                                            turns=[
                                                types.Content(
                                                    role="user",
                                                    parts=[types.Part.from_text(text=payload["text"])]
                                                )
                                            ],
                                            turn_complete=True
                                        )
                                    elif hasattr(session, "send"):
                                        await session.send(
                                            input=types.Content(
                                                parts=[types.Part.from_text(text=payload["text"])]
                                            ),
                                            end_of_turn=True,
                                        )
                                elif msg_type == "ping":
                                    await websocket.send_json({"type": "pong"})
                            except json.JSONDecodeError:
                                # Raw string fallback
                                if hasattr(session, "send_client_content"):
                                    await session.send_client_content(
                                        turns=[
                                            types.Content(
                                                role="user",
                                                parts=[types.Part.from_text(text=text_data)]
                                            )
                                        ],
                                        turn_complete=True
                                    )
                                elif hasattr(session, "send"):
                                    await session.send(
                                        input=types.Content(
                                            parts=[types.Part.from_text(text=text_data)]
                                        ),
                                        end_of_turn=True,
                                    )

                except (WebSocketDisconnect, RuntimeError):
                    logger.info("Senior user closed client connection (upstream).")
                except asyncio.CancelledError:
                    pass
                except Exception as up_err:
                    logger.error(f"Error in upstream audio stream: {up_err}", exc_info=True)

            # ----------------------------------------------------------------
            # DOWNSTREAM LOOP: Hardened Gemini Live API -> Browser
            # ----------------------------------------------------------------
            async def downstream_loop():
                try:
                    async for response in session.receive():
                        # Protect each individual chunk processing from terminating the entire loop
                        try:
                            # 1. Handle Model Speech Audio & Transcripts
                            server_content = getattr(response, "server_content", None)
                            if server_content is not None:
                                model_turn = getattr(server_content, "model_turn", None)
                                if model_turn is not None and getattr(model_turn, "parts", None):
                                    for part in model_turn.parts:
                                        # Audio stream delivery
                                        inline_data = getattr(part, "inline_data", None)
                                        if inline_data is not None and getattr(inline_data, "data", None):
                                            try:
                                                await websocket.send_bytes(inline_data.data)
                                            except Exception as send_bytes_err:
                                                logger.warning(f"Failed to send audio bytes: {send_bytes_err}")

                                        # Optional text transcript delivery
                                        part_text = getattr(part, "text", None)
                                        if part_text:
                                            try:
                                                await websocket.send_json({
                                                    "type": "transcript",
                                                    "role": "assistant",
                                                    "text": part_text,
                                                })
                                            except Exception as send_text_err:
                                                logger.warning(f"Failed to send transcript JSON: {send_text_err}")

                                # Turn Completion Handling (Notify frontend to sync buffer playback)
                                if getattr(server_content, "turn_complete", False):
                                    try:
                                        await websocket.send_json({"type": "turn_complete"})
                                    except Exception:
                                        pass

                                # Barge-in Interruption Handling
                                if getattr(server_content, "interrupted", False):
                                    try:
                                        await websocket.send_json({"type": "interrupted"})
                                    except Exception:
                                        pass

                            # 2. Handle Tool / Function Calls (Immediate Unblocking & Non-Blocking Logging)
                            tool_call = getattr(response, "tool_call", None)
                            if tool_call is not None and getattr(tool_call, "function_calls", None):
                                function_responses = []

                                for fc in tool_call.function_calls:
                                    call_id = getattr(fc, "id", None)
                                    call_name = getattr(fc, "name", None)
                                    raw_args = getattr(fc, "args", None)
                                    call_args = dict(raw_args) if raw_args is not None else {}

                                    logger.info(f"Executing Agent Tool: {call_name} (ID: {call_id})")

                                    # Notify UI of action execution
                                    try:
                                        await websocket.send_json({
                                            "type": "tool_executed",
                                            "tool": call_name,
                                            "name": call_name,
                                            "args": call_args,
                                        })
                                    except Exception:
                                        pass

                                    # Wrap all database/tool writes in asyncio.create_task() to prevent blocking the stream
                                    if call_name == "tool_log_tech_support":
                                        asyncio.create_task(async_log_tech_support(call_args))
                                    elif call_name == "tool_log_companion_task":
                                        asyncio.create_task(async_log_companion_task(call_args))
                                    elif call_name == "tool_trigger_urgent_alert":
                                        asyncio.create_task(async_trigger_urgent_alert(call_args))
                                        try:
                                            await websocket.send_json({
                                                "type": "alert",
                                                "level": "URGENT",
                                                "reason": call_args.get("details", "Wellness alert triggered"),
                                            })
                                        except Exception:
                                            pass

                                    # Build response payload for Live Session unblocking
                                    function_responses.append(
                                        types.FunctionResponse(
                                            id=call_id,
                                            name=call_name,
                                            response={"output": {"status": "ok", "message": "Task processed successfully."}},
                                        )
                                    )

                                # Send tool response back to Gemini immediately to unblock voice reply
                                if function_responses:
                                    try:
                                        if hasattr(session, "send_tool_response"):
                                            await session.send_tool_response(function_responses=function_responses)
                                        elif hasattr(session, "send"):
                                            try:
                                                await session.send(
                                                    input=types.LiveClientToolResponse(
                                                        function_responses=function_responses
                                                    )
                                                )
                                            except TypeError:
                                                await session.send(
                                                    types.LiveClientToolResponse(
                                                        function_responses=function_responses
                                                    )
                                                )
                                    except Exception as tool_resp_err:
                                        logger.error(f"Error sending tool response to Gemini: {tool_resp_err}")

                        except Exception as chunk_err:
                            logger.warning(f"Handled benign chunk variation in downstream loop: {chunk_err}")
                            continue

                except (WebSocketDisconnect, RuntimeError):
                    logger.info("Senior client disconnected (downstream).")
                except asyncio.CancelledError:
                    pass
                except Exception as down_err:
                    logger.error(f"Error in downstream audio stream: {down_err}", exc_info=True)

            # Run upstream and downstream concurrently with FIRST_EXCEPTION so tasks stay alive properly
            upstream_task = asyncio.create_task(upstream_loop())
            downstream_task = asyncio.create_task(downstream_loop())

            done, pending = await asyncio.wait(
                [upstream_task, downstream_task],
                return_when=asyncio.FIRST_EXCEPTION,
            )

            for task in pending:
                task.cancel()

    except WebSocketDisconnect:
        logger.info("WebSocket gracefully disconnected by senior client.")
    except Exception as e:
        logger.error(f"Live API streaming session error: {e}", exc_info=True)
        try:
            await websocket.send_json(
                {
                    "type": "status",
                    "status": "error",
                    "message": "Connection to KinAssist AI voice companion was interrupted.",
                }
            )
            await websocket.close()
        except Exception:
            pass


# Route attachments for both standard WebSocket endpoints
@app.websocket("/ws/live")
async def websocket_endpoint_live(websocket: WebSocket):
    await handle_live_session(websocket)


@app.websocket("/ws")
async def websocket_endpoint_default(websocket: WebSocket):
    await handle_live_session(websocket)


# ============================================================================
# APPLICATION ENTRYPOINT (CLOUD RUN / LOCAL)
# ============================================================================
if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8080))
    logger.info(f"Starting KinAssist AI Voice Server on port {port}...")
    uvicorn.run("main:app", host="0.0.0.0", port=port, log_level="info")
