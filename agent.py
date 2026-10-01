import logging
import os

from dotenv import load_dotenv
from livekit.agents import Agent, AgentServer, AgentSession, JobContext, cli, room_io
from livekit.agents.voice import VoiceActivityVideoSampler
from livekit.plugins import openai, tavus
from openai.types.realtime.realtime_audio_input_turn_detection import ServerVad

load_dotenv()
logger = logging.getLogger("video-agent")

INSTRUCTIONS = """You are a friendly, concise video assistant on a live call.
You can see the user through their camera or screen share, and they can see you as a video avatar.
Use what you see when it is relevant, but don't narrate the video unless asked.
If the user asks about something visual and no video is on, ask them to turn on their camera or share their screen.
Your replies are spoken aloud, so keep them short and conversational: one to three sentences.
Never use markdown, lists, emojis, or special characters.
Always speak English, even if the user's words sound like another language.
If you don't know something, say so plainly."""


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=INSTRUCTIONS)


server = AgentServer()


@server.rtc_session()
async def entrypoint(ctx: JobContext) -> None:
    await ctx.connect()

    session = AgentSession(
        llm=openai.realtime.RealtimeModel(
            model="gpt-realtime",
            voice="marin",
            # Reply after 0.5 s of silence. The default (semantic VAD) can wait several
            # seconds after short phrases like "hello" in case the user continues.
            turn_detection=ServerVad(
                type="server_vad",
                threshold=0.5,
                prefix_padding_ms=300,
                silence_duration_ms=500,
                create_response=True,
                interrupt_response=True,
            ),
        ),
        # Every sampled frame stays in the model's context as an image, so fewer frames
        # keep replies fast: one every 2 s while the user speaks, one every 10 s otherwise.
        video_sampler=VoiceActivityVideoSampler(speaking_fps=0.5, silent_fps=0.1),
    )

    # The avatar joins as a second participant and publishes the agent's audio and video.
    # Without a Tavus key the agent publishes its own audio and runs as voice + vision only.
    use_avatar = bool(os.getenv("TAVUS_API_KEY"))
    if use_avatar:
        avatar = tavus.AvatarSession()  # face comes from TAVUS_FACE_ID, else Tavus's stock face
        await avatar.start(session, room=ctx.room)
        await avatar.wait_for_join()
    else:
        logger.warning("TAVUS_API_KEY is not set, starting without an avatar")

    await session.start(
        agent=Assistant(),
        room=ctx.room,
        room_options=room_io.RoomOptions(video_input=True, audio_output=not use_avatar),
    )
    await session.generate_reply(instructions="Greet the user briefly and ask how you can help.")


if __name__ == "__main__":
    cli.run_app(server)
