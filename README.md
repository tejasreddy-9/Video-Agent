# LiveKit Video Agent POC

A real-time video assistant you can talk to from the browser, built on [LiveKit Agents](https://docs.livekit.io/agents/). The agent sees you through your camera or screen share, and appears as a lip-synced video avatar.

```
Browser (mic + camera/screen)  ──WebRTC──>  LiveKit Cloud  ──>  agent.py
                                                                 └─ OpenAI Realtime (gpt-realtime): hears, sees, speaks
                                                                        │ agent audio
Browser (avatar video + audio) <──WebRTC──  LiveKit Cloud  <──  Tavus avatar worker
```

The OpenAI Realtime model handles listening, vision, turn-taking and speech in one model. Its speech is sent to Tavus, which joins the room as a second participant and publishes the talking avatar. You can interrupt the agent mid-sentence.

## Project structure

| File | Purpose |
|---|---|
| `agent.py` | The video agent: realtime model, live video input, avatar, instructions |
| `server.py` | Small web server: serves the page and issues LiveKit access tokens |
| `frontend/index.html` | Browser client: avatar video, self view, camera and screen share, live transcript |
| `.env.example` | Template for the required keys |

## Prerequisites

- Python 3.10 – 3.14
- A [LiveKit Cloud](https://cloud.livekit.io) project (free tier is enough)
- An [OpenAI](https://platform.openai.com) API key with access to the Realtime API
- A [Tavus](https://platform.tavus.io) API key for the avatar (optional, see below)

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill it in:

| Variable | Where to find it |
|---|---|
| `LIVEKIT_URL` | LiveKit Cloud → Settings → Project → WebSocket URL (`wss://<project>.livekit.cloud`) |
| `LIVEKIT_API_KEY` / `LIVEKIT_API_SECRET` | LiveKit Cloud → Settings → Keys (same project as the URL) |
| `OPENAI_API_KEY` | OpenAI dashboard → API keys |
| `TAVUS_API_KEY` | Tavus platform → API keys. Leave empty to run without the avatar |
| `TAVUS_FACE_ID` | Optional. A [stock face](https://docs.tavus.io/sections/faces/stock-faces) or your own. Empty uses Tavus's default face |

`.env` is git-ignored. Never put real keys in `.env.example`.

Without `TAVUS_API_KEY` the agent still hears, sees and speaks; the video panel just stays empty.

## Run

Two terminals:

```bash
python agent.py dev    # terminal 1: the agent
python server.py       # terminal 2: the web page
```

Open http://localhost:8080 in Chrome or Edge, click **Start conversation** and allow microphone and camera access. The agent joins automatically and greets you. Each click creates a fresh room.

- **Camera off / on** stops or resumes sending your camera.
- **Share screen** lets the agent look at a window or your whole screen instead.

If port 8080 is taken, set another one: `PORT=9000 python server.py` (PowerShell: `$env:PORT=9000; python server.py`).

## Customizing

All in `agent.py`:

- **Personality** — edit `INSTRUCTIONS`.
- **Voice** — `voice="marin"`; other options include `cedar`, `alloy`, `ash`, `coral`, `echo`, `sage`, `shimmer`.
- **Model** — `openai.realtime.RealtimeModel(model=...)`.
- **Avatar face** — set `TAVUS_FACE_ID` in `.env`.
- **Turn-taking** — `ServerVad(silence_duration_ms=500)`: the agent replies after half a second of silence. Raise it if the agent cuts you off mid-thought; lower it for faster replies.
- **How often the agent looks** — `VoiceActivityVideoSampler(speaking_fps=0.5, silent_fps=0.1)`: one frame every 2 s while you speak, one every 10 s otherwise. Every frame stays in the model's context as an image, so higher rates make replies slower and calls more expensive.

## Cost notes

- Every video frame is sent to the model as an image and uses input tokens, so long calls with the camera on cost noticeably more than voice only. Turn the camera off when it isn't needed.
- Tavus bills per minute of avatar video.

## Known limitations

- The agent watches only the most recently published video track, so a screen share takes over from the camera. Switching back to the camera after you stop sharing has not been tested.
- If the voice POC agent is running against the same LiveKit project, either agent may pick up a new room. Run only one at a time, or give them different agent names with explicit dispatch.
- `python agent.py dev` prints a deprecation notice. It still works; the replacement is `lk agent dev` from the [LiveKit CLI](https://docs.livekit.io/reference/developer-tools/livekit-cli/).
- `server.py` hands a token to anyone who can reach it. That's fine on localhost, but add authentication before exposing it publicly.
