import os
import uuid
from pathlib import Path

from aiohttp import web
from dotenv import load_dotenv
from livekit import api

load_dotenv()

FRONTEND = Path(__file__).parent / "frontend" / "index.html"


async def index(_: web.Request) -> web.FileResponse:
    return web.FileResponse(FRONTEND)


async def token(_: web.Request) -> web.Response:
    room = f"video-poc-{uuid.uuid4().hex[:8]}"
    identity = f"user-{uuid.uuid4().hex[:6]}"
    jwt = (
        api.AccessToken(os.environ["LIVEKIT_API_KEY"], os.environ["LIVEKIT_API_SECRET"])
        .with_identity(identity)
        .with_name("POC User")
        .with_grants(api.VideoGrants(room_join=True, room=room))
        .to_jwt()
    )
    return web.json_response({"url": os.environ["LIVEKIT_URL"], "token": jwt, "room": room})


app = web.Application()
app.add_routes([web.get("/", index), web.get("/token", token)])

if __name__ == "__main__":
    web.run_app(app, host="127.0.0.1", port=int(os.environ.get("PORT", "8080")))
