# Jarvis - AI Voice Assistant

A sophisticated AI voice assistant with vision capabilities, persistent memory, and calendar integration. Built with [LiveKit Agents](https://github.com/livekit/agents) and powered by Google Gemini, ElevenLabs, and Deepgram.

## Features

- **Voice Interaction** - Natural conversation using Deepgram STT and ElevenLabs TTS
- **Vision Capabilities** - Analyze video streams and screen shares in real-time
- **Persistent Memory** - Remember user preferences and context across sessions using Mem0
- **Calendar Integration** - Manage calendar events via MCP server
- **Web Search** - Search the web using Perplexity AI
- **Email** - Send emails through Gmail
- **Weather** - Get current weather for any city
- **Background Audio** - Ambient sounds and typing feedback during processing

## Tech Stack

- **LLM**: Google Gemini 2.5 Flash
- **Speech-to-Text**: Deepgram Nova 3
- **Text-to-Speech**: ElevenLabs
- **Memory**: Mem0
- **Web Search**: Perplexity AI
- **Framework**: LiveKit Agents

## Setup

### Prerequisites

- Python 3.9+
- [uv](https://github.com/astral-sh/uv) package manager
- LiveKit Cloud account

### Installation

1. Clone the repository:

```bash
git clone https://github.com/akshay-baiplawat/jarvis-agent.git
cd jarvis-agent
```

2. Install dependencies:

```bash
uv sync
```

3. Create a `.env` file with your credentials:

```env
# LiveKit
LIVEKIT_URL=your_livekit_url
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret

# Google Gemini
GOOGLE_API_KEY=your_google_api_key

# ElevenLabs
ELEVEN_API_KEY=your_elevenlabs_key

# Deepgram
DEEPGRAM_API_KEY=your_deepgram_key

# Mem0 (Memory)
MEM0_API_KEY=your_mem0_key
USER_ID=your_user_id

# Perplexity (Web Search)
PERPLEXITY_API_KEY=your_perplexity_key

# Gmail (Email)
GMAIL_USER=your_gmail
GMAIL_APP_PASSWORD=your_app_password

# Calendar MCP
CALENDAR_MCP_URL=your_mcp_server_url

# User Context
USER_LOCATION=your_location
USER_TIMEZONE=your_timezone
```

4. Set up Google Calendar credentials:
   - Create OAuth credentials in Google Cloud Console
   - Save as `src/calendar_credentials.json`

### Running the Agent

Download required models:

```bash
uv run python src/agent.py download-files
```

Run in console mode (terminal):

```bash
uv run python src/agent.py console
```

Run for frontend/telephony:

```bash
uv run python src/agent.py dev
```

Production:

```bash
uv run python src/agent.py start
```

## Tools Available

| Tool | Description |
| ---- | ----------- |
| `get_weather` | Get current weather for a city |
| `search_web` | Search the web via Perplexity AI |
| `send_email` | Send emails through Gmail |
| `save_memory` | Store information for future sessions |
| `search_memories` | Search stored memories |
| `get_all_memories` | Retrieve all stored memories |
| Calendar MCP | Manage calendar events |

## Project Structure

```text
jarvis_agent/
├── src/
│   ├── agent.py              # Main agent with vision capabilities
│   ├── prompts.py            # Jarvis persona and instructions
│   ├── tool.py               # Tool implementations
│   └── calendar_credentials.json
├── pyproject.toml
└── README.md
```

## Personality

Jarvis embodies a sophisticated British butler merged with cutting-edge AI:

- Elegant vocabulary and subtle wit
- Professional warmth without being overly friendly
- One-sentence responses for elegance
- Created by Akshay

## License

MIT License
