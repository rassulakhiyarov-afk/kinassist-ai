import express from "express";
import http from "http";
import path from "path";
import fs from "fs";
import { WebSocketServer, WebSocket } from "ws";
import { GoogleGenAI, Modality, Type } from "@google/genai";
import { createServer as createViteServer } from "vite";
import dotenv from "dotenv";

dotenv.config();

const PORT = 3000;

// Empathetic Multilingual System Instruction for KinAssist AI
const SYSTEM_INSTRUCTION = `
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
  3. Call the tool tool_log_tech_support to log their issue and steps for their family and caregivers.
  4. Always check in patiently after giving instructions.

ACTION B: COMPANIONSHIP & DAILY TASKS / SCHEDULES
- If the senior talks about daily routines, schedules, medications, meals, memories, or tasks:
  1. Listen with deep empathy in their language, celebrate their memories, and validate their feelings.
  2. If they mention an appointment, medication time, grocery item, or task to remember, warmly acknowledge it in their language and call tool_log_companion_task to store it structured in the logs.
  3. Encourage them gently and ask an open-ended, pleasant question to continue the uplifting conversation.

ACTION C: URGENT SENTINEL & WELLNESS EMERGENCIES
- If the senior mentions physical pain, distress, fear (e.g., "I'm scared", "мені страшно", "боюсь", "me duele"), a fall, severe dizziness, shortness of breath, feeling unsafe, or needing immediate help:
  1. Remain completely calm, soothing, and deeply reassuring in their spoken language. Tell them immediately that they are safe, they are not alone, and that help is being alerted right away.
  2. Instruct them gently to stay still, breathe slowly, and remain safe.
  3. Immediately call tool_trigger_urgent_alert with the exact severity and context (status 'URGENT').
  4. Continue speaking softly in their language to keep them comforted and reassured while the alert is dispatched.
`;

const KINASSIST_TOOLS = [
  {
    functionDeclarations: [
      {
        name: "tool_log_tech_support",
        description: "Logs a technology assistance session or troubleshooting step for the senior without technical jargon.",
        parameters: {
          type: Type.OBJECT,
          properties: {
            device_or_app: {
              type: Type.STRING,
              description: "The device, appliance, or application name (e.g. TV Remote, iPad, Phone).",
            },
            issue_description: {
              type: Type.STRING,
              description: "Summary of the senior's question or issue.",
            },
            steps_provided: {
              type: Type.STRING,
              description: "The simplified, jargon-free steps provided to the senior.",
            },
            resolved: {
              type: Type.BOOLEAN,
              description: "Whether the issue was resolved during the step.",
            },
          },
          required: ["device_or_app", "issue_description"],
        },
      },
      {
        name: "tool_log_companion_task",
        description: "Logs a daily schedule item, reminder, calendar task, medication note, or companionship memory to Firestore collection 'kinassist_logs'.",
        parameters: {
          type: Type.OBJECT,
          properties: {
            task_type: {
              type: Type.STRING,
              description: "Type of task: 'medication', 'appointment', 'calendar', 'reminder', 'routine', or 'memory'.",
            },
            description: {
              type: Type.STRING,
              description: "Detailed description of the task, routine, or memory.",
            },
            scheduled_time: {
              type: Type.STRING,
              description: "Time or date mentioned for the schedule or reminder.",
            },
          },
          required: ["task_type", "description"],
        },
      },
      {
        name: "tool_trigger_urgent_alert",
        description: "Triggers an urgent sentinel distress alert to caregivers and emergency contacts, flagging document as URGENT.",
        parameters: {
          type: Type.OBJECT,
          properties: {
            emergency_type: {
              type: Type.STRING,
              description: "Nature of the emergency or distress (e.g., fall, severe pain, panic, dizziness, chest pain).",
            },
            details: {
              type: Type.STRING,
              description: "Contextual details of the emergency situation.",
            },
            severity: {
              type: Type.STRING,
              description: "Severity level: 'CRITICAL', 'HIGH', or 'MEDIUM'.",
            },
          },
          required: ["emergency_type", "details", "severity"],
        },
      },
    ],
  },
];

async function startServer() {
  const app = express();
  app.use(express.json());

  // Health and API routes
  app.get("/healthz", (req, res) => {
    res.json({ status: "healthy", service: "KinAssist AI Voice Backend" });
  });

  app.get("/health", (req, res) => {
    res.json({ status: "healthy", service: "KinAssist AI Voice Backend" });
  });

  // Create HTTP server
  const server = http.createServer(app);

  // Attach WebSocket Server
  const wss = new WebSocketServer({ noServer: true });

  server.on("upgrade", (request, socket, head) => {
    try {
      const url = new URL(request.url || "/", `http://${request.headers.host || "localhost"}`);
      const pathname = url.pathname;
      if (pathname === "/ws/live" || pathname === "/ws") {
        wss.handleUpgrade(request, socket, head, (ws) => {
          wss.emit("connection", ws, request);
        });
      }
      // Note: do not destroy socket here for non-matching paths so Vite HMR / dev proxies are not aborted
    } catch (err) {
      console.error("[KinAssist AI] Upgrade handler error:", err);
    }
  });

  // Handle client WebSocket connections
  wss.on("connection", async (clientWs: WebSocket) => {
    console.log("[KinAssist AI] Senior client connected to live voice stream");

    const apiKey = process.env.GEMINI_API_KEY;
    const ai = new GoogleGenAI({ apiKey: apiKey || "" });

    // Send ready notice to client
    clientWs.send(JSON.stringify({ type: "session_ready", model: "gemini-3.1-flash-live-preview" }));

    let liveSession: any = null;

    try {
      liveSession = await ai.live.connect({
        model: "gemini-3.1-flash-live-preview",
        config: {
          responseModalities: [Modality.AUDIO],
          speechConfig: {
            voiceConfig: {
              prebuiltVoiceConfig: {
                voiceName: "Aoede", // Warm, empathetic voice
              },
            },
          },
          systemInstruction: SYSTEM_INSTRUCTION,
          tools: KINASSIST_TOOLS as any,
        },
        callbacks: {
          onmessage: async (message: any) => {
            try {
              // 1. Audio data from model
              const parts = message.serverContent?.modelTurn?.parts;
              if (parts && Array.isArray(parts)) {
                for (const part of parts) {
                  if (part.inlineData?.data) {
                    const audioBuffer = Buffer.from(part.inlineData.data, "base64");
                    if (clientWs.readyState === WebSocket.OPEN) {
                      clientWs.send(audioBuffer);
                    }
                  }
                  if (part.text) {
                    if (clientWs.readyState === WebSocket.OPEN) {
                      clientWs.send(
                        JSON.stringify({
                          type: "transcript",
                          role: "assistant",
                          text: part.text,
                        })
                      );
                    }
                  }
                }
              }

              // 2. Interruption / Turn Complete events
              if (message.serverContent?.turnComplete) {
                if (clientWs.readyState === WebSocket.OPEN) {
                  clientWs.send(JSON.stringify({ type: "turn_complete" }));
                }
              }

              if (message.serverContent?.interrupted) {
                if (clientWs.readyState === WebSocket.OPEN) {
                  clientWs.send(JSON.stringify({ type: "interrupted" }));
                }
              }

              // 3. Tool Calls (Function executions)
              if (message.toolCall?.functionCalls) {
                const functionResponses: any[] = [];
                for (const call of message.toolCall.functionCalls) {
                  console.log(`[KinAssist AI] Tool Execution: ${call.name}`, call.args);

                  if (clientWs.readyState === WebSocket.OPEN) {
                    clientWs.send(
                      JSON.stringify({
                        type: "tool_executed",
                        tool: call.name,
                        name: call.name,
                        args: call.args,
                      })
                    );

                    if (call.name === "tool_trigger_urgent_alert") {
                      clientWs.send(
                        JSON.stringify({
                          type: "alert",
                          level: "URGENT",
                          reason: call.args?.details || "Wellness alert triggered",
                        })
                      );
                    }
                  }

                  functionResponses.push({
                    id: call.id,
                    name: call.name,
                    response: { output: { status: "ok", message: "Processed successfully" } },
                  });
                }

                // Immediately send tool response back to unblock model
                if (functionResponses.length > 0 && liveSession?.sendToolResponse) {
                  liveSession.sendToolResponse({ functionResponses });
                }
              }
            } catch (err) {
              console.error("[KinAssist AI] Error in Live onmessage handler:", err);
            }
          },
          onclose: () => {
            console.log("[KinAssist AI] Gemini Live session closed");
          },
          onerror: (err: any) => {
            console.error("[KinAssist AI] Gemini Live session error:", err);
          },
        },
      });
    } catch (err: any) {
      console.error("[KinAssist AI] Failed to initialize live session:", err);
      if (clientWs.readyState === WebSocket.OPEN) {
        clientWs.send(
          JSON.stringify({
            type: "status",
            status: "ready_local",
            message: "Live voice connection initialized.",
          })
        );
      }
    }

    clientWs.on("message", (data: any, isBinary: boolean) => {
      try {
        if (isBinary || Buffer.isBuffer(data)) {
          const base64Audio = (data as Buffer).toString("base64");
          if (liveSession?.sendRealtimeInput) {
            liveSession.sendRealtimeInput({
              audio: {
                data: base64Audio,
                mimeType: "audio/pcm;rate=16000",
              },
            });
          }
        } else {
          const textMsg = data.toString();
          try {
            const payload = JSON.parse(textMsg);
            if (payload.type === "urgent_trigger") {
              if (liveSession?.sendClientContent) {
                liveSession.sendClientContent({
                  turns: [
                    {
                      role: "user",
                      parts: [
                        {
                          text: `[URGENT SENIOR EVENT: Emergency button pressed. Reason: ${payload.reason || "Help needed"}. Speak immediately with warm comfort and assurance that family and caregivers are being alerted.]`,
                        },
                      ],
                    },
                  ],
                  turnComplete: true,
                });
              }
            } else if (payload.type === "text" && payload.text) {
              if (liveSession?.sendClientContent) {
                liveSession.sendClientContent({
                  turns: [{ role: "user", parts: [{ text: payload.text }] }],
                  turnComplete: true,
                });
              }
            }
          } catch {
            // raw string fallback
            if (liveSession?.sendClientContent) {
              liveSession.sendClientContent({
                turns: [{ role: "user", parts: [{ text: textMsg }] }],
                turnComplete: true,
              });
            }
          }
        }
      } catch (sendErr) {
        console.error("[KinAssist AI] Error sending input to live session:", sendErr);
      }
    });

    clientWs.on("close", () => {
      console.log("[KinAssist AI] Senior client disconnected");
      try {
        if (liveSession?.close) {
          liveSession.close();
        }
      } catch {}
    });
  });

  // Vite middleware for development
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);

    // Fallback handler for serving index.html transformed by Vite
    app.use("*", async (req, res, next) => {
      const url = req.originalUrl;
      try {
        const templatePath = path.resolve(process.cwd(), "index.html");
        if (fs.existsSync(templatePath)) {
          let template = fs.readFileSync(templatePath, "utf-8");
          template = await vite.transformIndexHtml(url, template);
          res.status(200).set({ "Content-Type": "text/html" }).end(template);
        } else {
          next();
        }
      } catch (e) {
        if (vite?.ssrFixStacktrace) {
          vite.ssrFixStacktrace(e as Error);
        }
        next(e);
      }
    });
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  server.listen(PORT, "0.0.0.0", () => {
    console.log(`KinAssist AI server running on http://0.0.0.0:${PORT}`);
  });
}

startServer().catch((err) => {
  console.error("Fatal startup error:", err);
});
