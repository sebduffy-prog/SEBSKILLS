---
name: realtime-voice-agent
category: voice-agents
description: >
  Build a low-latency speech-to-speech conversational voice agent with barge-in, natural
  turn-taking, and mid-call tool/function calls. Reach for it on "voice agent", "voice bot",
  "phone agent", "talk to my AI", "real-time audio", "speech-to-speech", "barge-in / interrupt",
  "Pipecat", "LiveKit Agents", or "OpenAI Realtime API". Covers the two production paths —
  a cascaded STT to LLM to TTS pipeline (Pipecat / LiveKit) and a single realtime S2S model
  (OpenAI Realtime) — plus VAD, endpointing, function tools, and telephony (Twilio/Daily) wiring.
when_to_use:
  - "You want a two-way spoken conversation (mic in, voice out) that responds in well under a second"
  - "The agent must handle barge-in — the user talks over it and it stops speaking and listens"
  - "You need turn-taking / endpointing so the agent knows when the user has finished a sentence"
  - "The agent must call tools or functions mid-conversation (look up an order, book a slot, hit an API)"
  - "You are wiring a voice bot to telephony (Twilio, Daily, SIP) or a browser WebRTC room"
  - "You are choosing between a cascaded STT to LLM to TTS pipeline and a single speech-to-speech model"
when_not_to_use:
  - "You only need one-shot text-to-speech or a voiceover file with no live conversation → use a plain TTS API call, not this"
  - "You are building a text-only chat or tool-using agent with no audio → use building-agents or claude-api instead"
  - "You need to transcribe an existing recording (batch STT) with no live turn-taking → use a batch Whisper/Deepgram call directly"
  - "You want to author a Claude Code skill or MCP server → use skill-creator or mcp-builder instead"
keywords:
  - voice agent
  - speech-to-speech
  - pipecat
  - livekit
  - openai realtime
  - barge-in
  - turn-taking
  - vad
  - endpointing
  - function calling
  - telephony
  - twilio
  - webrtc
  - low latency
  - stt
  - tts
  - conversational ai
similar_to:
  - building-agents
  - claude-api
  - mcp-builder
inputs_needed: >
  Python 3.10+ (Pipecat/LiveKit require ≥3.10; this Mac's system python3 is 3.9 — use a venv with a
  newer Python). Provider API keys for whichever services you pick: OPENAI_API_KEY (LLM or Realtime),
  DEEPGRAM_API_KEY (STT), CARTESIA_API_KEY or ELEVENLABS_API_KEY (TTS). Optional: a transport —
  Daily (DAILY_API_KEY) or LiveKit Cloud (LIVEKIT_URL/API_KEY/API_SECRET), or Twilio for phone calls.
produces: >
  A runnable async voice-agent script (Pipecat pipeline, LiveKit AgentSession, or OpenAI Realtime
  loop) with VAD-driven interruption, turn detection, mid-call function tools, and a transport
  (WebRTC browser room or telephony). Plus a decision guide for cascaded-vs-S2S and a latency checklist.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Realtime Voice Agent

Author a spoken, interruptible, tool-using AI agent that talks back in real time. Two proven
stacks are covered: **Pipecat** (framework-agnostic pipeline, self-hostable) and **LiveKit
Agents** (batteries-included, LiveKit Cloud transport). Both support two model topologies:
**cascaded** (STT → LLM → TTS — swappable, cheapest, easy transcripts, ~800ms–1.5s round trip) and
**speech-to-speech / S2S** (one realtime model in and out — ~300–500ms, most natural, pricier, less
introspectable).

## When to use

Use this when the deliverable is a **live two-way voice conversation** that must feel natural:
sub-second responses, barge-in (user cuts the agent off), real end-of-turn detection, and mid-call
function calls. For a one-shot TTS clip or a batch transcript this is overkill — see `when_not_to_use`.

## Prerequisites (honest)

- **Python ≥ 3.10.** Pipecat and LiveKit Agents both drop 3.9. On this Mac, `python3` is 3.9, so:
  `python3.11 -m venv .venv && source .venv/bin/activate` (install a newer Python via pyenv/uv first).
  If no ≥3.10 is available, use `uv`: `uv venv --python 3.11`.
- **Provider keys** in a `.env` (loaded with `python-dotenv`). Minimum for a cascaded bot:
  `OPENAI_API_KEY`, `DEEPGRAM_API_KEY`, `CARTESIA_API_KEY`.
- **A transport.** Local dev: Pipecat's built-in WebRTC needs no account. Browser rooms: Daily or
  LiveKit Cloud. Phone: Twilio Media Streams or a SIP trunk. Plus a **mic + speakers** (or a number) —
  realtime audio can't be tested from pure text.

Latency is dominated by network hops and TTS time-to-first-byte, not your code. Use streaming
services (Deepgram streaming STT, Cartesia/ElevenLabs streaming TTS) — never batch ones.

## Recipe A — Pipecat cascaded pipeline (STT → LLM → TTS, with barge-in)

Install (Pipecat groups pull the right SDKs):

```bash
uv add "pipecat-ai[silero,deepgram,openai,cartesia,webrtc]"   # or: pip install "pipecat-ai[...]"
```

The pipeline chains processors; the **user aggregator carries the Silero VAD analyzer**, which is
what detects speech start/stop and drives interruption. Import paths below are current on `main`:

```python
import os
from dotenv import load_dotenv
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import LLMRunFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.transports.base_transport import TransportParams

load_dotenv()

async def run_bot(transport):
    stt = DeepgramSTTService(api_key=os.environ["DEEPGRAM_API_KEY"])
    llm = OpenAILLMService(api_key=os.environ["OPENAI_API_KEY"], model="gpt-4o")
    tts = CartesiaTTSService(
        api_key=os.environ["CARTESIA_API_KEY"],
        voice_id="79a125e8-cd45-4c13-8a67-188112f4dd22",
    )

    context = LLMContext()
    context.set_messages([{"role": "system", "content":
        "You are a concise voice assistant. Reply in one or two short spoken sentences."}])
    user_agg, assistant_agg = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(vad_analyzer=SileroVADAnalyzer()),  # VAD fires interruptions
    )

    pipeline = Pipeline([
        transport.input(), stt, user_agg, llm, tts, transport.output(), assistant_agg,
    ])  # mic in → STT → user turn → LLM → TTS → speaker out → record what bot said

    task = PipelineTask(pipeline, params=PipelineParams(
        allow_interruptions=True,   # <- barge-in: user speech cancels in-flight bot speech
        enable_metrics=True, enable_usage_metrics=True,
    ))

    @transport.event_handler("on_client_connected")
    async def _(_t, _c):
        await task.queue_frames([LLMRunFrame()])  # greet first

    await PipelineRunner(handle_sigint=True).run(task)
```

`allow_interruptions=True` is the whole barge-in story: when Silero VAD detects the user speaking
while TTS is playing, Pipecat cancels the in-flight LLM+TTS frames and starts a fresh user turn.

**Local WebRTC transport** (no accounts): scaffold the browser test page with
`uv tool install "pipecat-ai[cli]"; pipecat init quickstart`. Swap TTS to
`pipecat.services.elevenlabs.tts.ElevenLabsTTSService` or STT to another provider by changing one
line — the pipeline shape is unchanged.

### Function tools mid-call (Pipecat)

Register tools on the LLM service; Pipecat pauses speaking, runs the call, feeds the result back:

```python
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema

async def check_order(params):
    order_id = params.arguments["order_id"]
    await params.result_callback({"status": "shipped", "eta": "Thursday"})

llm.register_function("check_order", check_order)
tools = ToolsSchema(standard_tools=[FunctionSchema(
    name="check_order", description="Look up an order's status",
    properties={"order_id": {"type": "string"}}, required=["order_id"],
)])
context = LLMContext(tools=tools)
```

## Recipe B — LiveKit Agents (AgentSession, turn detection, tools)

LiveKit bundles STT/LLM/TTS/VAD/turn-detection into one `AgentSession` and handles the WebRTC
room. Install with the plugins you need:

```bash
pip install "livekit-agents[openai,deepgram,cartesia,silero,turn-detector]"
```

```python
from livekit import agents
from livekit.agents import Agent, AgentSession, JobContext, RunContext, WorkerOptions, cli, function_tool
from livekit.plugins import openai, deepgram, cartesia, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

@function_tool
async def lookup_weather(context: RunContext, location: str) -> dict:
    """Look up the weather for a city."""
    return {"weather": "sunny", "temp_c": 21}

async def entrypoint(ctx: JobContext):
    session = AgentSession(
        stt=deepgram.STT(model="nova-3"),
        llm=openai.LLM(model="gpt-4o"),
        tts=cartesia.TTS(),
        vad=silero.VAD.load(),                     # voice activity → interruption
        turn_detection=MultilingualModel(),        # semantic end-of-turn, not just silence
    )
    agent = Agent(
        instructions="You are a concise voice assistant. Keep replies short.",
        tools=[lookup_weather],
    )
    await session.start(agent=agent, room=ctx.room)
    await session.generate_reply(instructions="Greet the user warmly and offer help.")

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
```

Barge-in is on by default in `AgentSession` (VAD-triggered). `turn_detection` uses a small
transformer to decide the user *actually finished* (avoids cutting them off at a natural pause) —
strictly better than raw silence timeouts. Run: `python agent.py dev` (connects to LiveKit Cloud).

> LiveKit Cloud also offers an `inference` gateway (`inference.STT("deepgram/nova-3")`, etc.) so you
> don't manage provider keys. The plugin form above works everywhere; prefer it off LiveKit Cloud.

## Recipe C — OpenAI Realtime (single speech-to-speech model)

Lowest latency, most natural. In Pipecat, replace the STT+LLM+TTS trio with one service:

```python
from pipecat.services.openai.realtime import OpenAIRealtimeLLMService  # (older: openai_realtime_beta)

llm = OpenAIRealtimeLLMService(
    api_key=os.environ["OPENAI_API_KEY"],
    model="gpt-realtime",   # verify current name; e.g. gpt-4o-realtime-preview-2025-06-03
)
# pipeline shrinks: [transport.input(), context_user_agg, llm, transport.output(), context_asst_agg]
```

The Realtime model does its own VAD/endpointing server-side (`turn_detection` in the session
config). Keep Pipecat's client-side interruption handling for clean barge-in. Tools are declared on
the session and the model emits `function_call` events.

Trade-off: S2S gives up the readable intermediate transcript and per-stage swappability. Use
cascaded when you need transcripts, content filtering between stages, or a specific brand voice;
use S2S when raw latency and prosody win.

## Verify

1. **Syntax**: `python -c "import ast; ast.parse(open('bot.py').read())"` (parses without a venv).
2. **Deps + keys**: in the venv, `python -c "import pipecat"` (or `import livekit.agents`), then
   `python -c "import os,dotenv; dotenv.load_dotenv(); assert os.getenv('OPENAI_API_KEY')"`.
3. **Live smoke test**: run the bot, open the WebRTC page (or dial the number), say "hello" — reply
   should land in under ~1.2s (cascaded) or ~0.5s (S2S).
4. **Barge-in test**: talk over the bot mid-sentence. It must stop within ~200–400ms and respond to
   what you just said, not finish the old sentence.
5. **Turn-taking test**: pause mid-sentence ("I'd like to book… uh…"). A good endpointer waits; a
   naive silence timeout wrongly barges in — tune VAD `stop_secs` / the turn detector if it does.
6. **Tool test**: ask something that triggers a function; confirm it runs and the result is spoken.

## Pitfalls

- **Python 3.9 will not install these.** Both frameworks require ≥3.10. Make the venv first.
- **Batch services kill the illusion.** Non-streaming STT/TTS add seconds — use streaming endpoints
  (Deepgram streaming, Cartesia/ElevenLabs streaming).
- **VAD too aggressive = the bot interrupts itself or the user.** Tune `stop_secs`; prefer a semantic
  turn detector (LiveKit `turn_detector`, Pipecat smart-turn) over raw silence for natural pauses.
- **No interruption handling = users talk over a monologuing bot.** Set `allow_interruptions=True`
  (Pipecat); it's on by default in LiveKit `AgentSession`. Always test barge-in explicitly.
- **Long replies feel laggy.** Prompt for *one or two short spoken sentences* and stream tokens so
  TTS starts on the first clause.
- **Model/version names drift fast.** Realtime IDs (`gpt-realtime` vs `gpt-4o-realtime-preview-...`)
  and package APIs change often — pin versions and re-verify class/model names against current docs.
- **Telephony sample rate.** Phone audio is 8kHz μ-law, browser is 48kHz. Match the transport's audio
  params or audio garbles; don't assume defaults handle resampling.
- **Cost surprises with S2S.** OpenAI Realtime bills audio in and out; cascaded (cheap LLM + Deepgram
  + Cartesia) is often 3–5× cheaper at high call volume.

## References

- Pipecat: https://docs.pipecat.ai (quickstart: `pipecat init quickstart`)
- LiveKit Agents: https://docs.livekit.io/agents/
- OpenAI Realtime: https://platform.openai.com/docs/guides/realtime
