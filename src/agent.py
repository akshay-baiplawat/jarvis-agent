from dotenv import load_dotenv
from livekit import agents, rtc
from livekit.agents import (
    AgentSession, 
    Agent, 
    RoomInputOptions,
    AutoSubscribe,
    ChatContext,
    JobContext,
    get_job_context,
    BackgroundAudioPlayer,     # Add this import
    AudioConfig,               # Add this import
    BuiltinAudioClip
)
from livekit.agents.llm import ImageContent, ChatMessage
from livekit.plugins import (
    google,
    elevenlabs,
    deepgram,
    noise_cancellation,
    silero,
)
from livekit.plugins.turn_detector.multilingual import MultilingualModel
import asyncio
import logging
from livekit.agents import mcp
import os
from mem0 import MemoryClient

from prompts import AGENT_INSTRUCTION, SESSION_INSTRUCTION
from tool import get_all_memories, get_weather, save_memory, save_memory_simple, save_memory_with_context, search_memories, search_web, send_email

load_dotenv(".env")
logger = logging.getLogger(__name__)

class VisionAssistant(Agent):
    def __init__(self, *, chat_ctx: ChatContext):
        super().__init__(
            instructions=AGENT_INSTRUCTION,
            chat_ctx=chat_ctx,
            tools=[
                get_weather, 
                search_web, 
                send_email,
                save_memory,
                save_memory_simple,
                save_memory_with_context,
                search_memories,
                get_all_memories
            ],
            mcp_servers=[
                mcp.MCPServerHTTP(os.getenv("CALENDAR_MCP_URL"))
            ],
        )
        self._latest_frame = None
        self._video_stream = None
        self._tasks = []
    
    async def on_enter(self):
        """Called when the agent enters the room"""
        room = get_job_context().room

        # Find the first video track (if any) from the remote participant
        for participant in room.remote_participants.values():
            video_tracks = [
                publication.track for publication in participant.track_publications.values() 
                if publication.track and publication.track.kind == rtc.TrackKind.KIND_VIDEO
            ]
            if video_tracks:
                self._create_video_stream(video_tracks[0])
                break
        
        # Watch for new video tracks not yet published
        @room.on("track_subscribed")
        def on_track_subscribed(track: rtc.Track, publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
            if track.kind == rtc.TrackKind.KIND_VIDEO:
                logger.info(f"New video track subscribed: {track.sid}")
                self._create_video_stream(track)
    
    async def on_user_turn_completed(self, turn_ctx: ChatContext, new_message: ChatMessage) -> None:
        """Add the latest video frame to each user message for context"""
        if self._latest_frame:
            # Add the current video frame to the user's message
            if isinstance(new_message.content, str):
                new_message.content = [new_message.content]
            elif not isinstance(new_message.content, list):
                new_message.content = [str(new_message.content)]
            
            new_message.content.append(ImageContent(image=self._latest_frame))
            logger.debug("Added latest video frame to user message")
    
    def _create_video_stream(self, track: rtc.Track):
        """Create a video stream to capture frames from the user's video track"""
        # Close any existing stream (we only want one at a time)
        if self._video_stream is not None:
            asyncio.create_task(self._video_stream.aclose())

        # Create a new stream to receive frames    
        self._video_stream = rtc.VideoStream(track)
        
        async def read_stream():
            try:
                async for event in self._video_stream:
                    # Store the latest frame for use later
                    self._latest_frame = event.frame
                    logger.debug("Captured new video frame")
            except Exception as e:
                logger.error(f"Error reading video stream: {e}")
        
        # Store the async task
        task = asyncio.create_task(read_stream())
        task.add_done_callback(lambda t: self._tasks.remove(t) if t in self._tasks else None)
        self._tasks.append(task)

async def entrypoint(ctx: JobContext):
    logger.info(f"Starting vision agent in room: {ctx.room.name}")
    
    await ctx.connect(auto_subscribe=AutoSubscribe.SUBSCRIBE_ALL)

    # Initialize Mem0 client
    try:
        mem0_client = MemoryClient(api_key=os.getenv("MEM0_API_KEY"))
        user_id = os.environ.get("USER_ID", "default_user")
        
        # Search for recent context
        recent_memories = mem0_client.search(
            "recent preferences schedule meetings", 
            user_id=user_id, 
            limit=5
        )
        
        if recent_memories:
            memory_context = "RECENT MEMORY CONTEXT:\n" + "\n".join([f"• {m['memory']}" for m in recent_memories])
        else:
            memory_context = "RECENT MEMORY CONTEXT:\n• No previous memories found - this is a fresh start"
            
        logger.info(f"Loaded {len(recent_memories)} memories for user {user_id}")
        
    except Exception as e:
        logger.warning(f"Could not load memories: {e}")
        memory_context = "RECENT MEMORY CONTEXT:\n• Memory system unavailable"
    
    # Build the initial ChatContext
    initial_ctx = ChatContext()
    initial_ctx.add_message(
        role="system",
        content=(
            "You are a helpful voice assistant Jarvis with vision capabilities. "
            "When you receive images from the user's camera or screen sharing, "
            "naturally describe what you see and keep responses concise.\n\n"
            f"{memory_context}\n\n"
            "Use the memory context above to provide more personalized responses. "
            "Automatically save important user information using the save_memory tool."
        )
    )
    
    calendar_mcp = mcp.MCPServerHTTP(os.getenv("CALENDAR_MCP_URL"))
    # Create the AgentSession (no chat_ctx here)
    session = AgentSession(
        stt=deepgram.STT(model="nova-3", language="en"), # model="nova-2", language="en" multi English will we always more accurate 
        llm=google.LLM(
            model="gemini-2.5-flash",
            temperature=0.3
            ),
        tts=elevenlabs.TTS(
            voice_id="ErXwobaYiN019PkySvjV"
            ),
        vad=silero.VAD.load(),
        mcp_servers=[calendar_mcp],
    )
    
    # Instantiate your agent with the initial context
    agent = VisionAssistant(
        chat_ctx=initial_ctx
        )
    
    # Start 
    await session.start(
        room=ctx.room,
        agent=agent,
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    await ctx.connect()

        # Add Background Audio Player with thinking sounds
    background_audio = BackgroundAudioPlayer(
        # Optional: Play subtle office ambience in background
        ambient_sound=AudioConfig(BuiltinAudioClip.OFFICE_AMBIENCE, volume=0.3),
        
        # Play "thinking" sounds when agent processes tools/tasks
        thinking_sound=[
            AudioConfig(BuiltinAudioClip.KEYBOARD_TYPING, volume=0.6),
            AudioConfig(BuiltinAudioClip.KEYBOARD_TYPING2, volume=0.5),
        ],
    )

    # Start the background audio
    await background_audio.start(room=ctx.room, agent_session=session)

    await session.generate_reply(
        instructions=SESSION_INSTRUCTION,
    )

if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
