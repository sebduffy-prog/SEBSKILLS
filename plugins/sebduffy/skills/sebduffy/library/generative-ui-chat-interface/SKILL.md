---
name: generative-ui-chat-interface
category: frontend-and-design
description: >
  Build a streaming AI chat / generative-UI front-end with the Vercel AI SDK v7
  (useChat + DefaultChatTransport) and AI Elements. Use it whenever you need a
  token-streaming chatbot, assistant panel, "chat with your data" widget, RAG
  answer box, or copilot UI in React/Next.js — with message parts rendering,
  stop/regenerate, streaming status, reasoning traces, and sources. Grounds every
  import, hook property and route handler against the real v7 API so it compiles.
when_to_use:
  - Building a streaming chatbot or assistant panel in React/Next.js that renders tokens as they arrive
  - Wiring the client useChat hook to a server route that calls streamText and streams UI messages back
  - Rendering assistant output as message parts (text, reasoning, tool calls, sources) instead of a plain string
  - Adding stop, regenerate, streaming-status and error handling to an existing chat box
  - Dropping in polished shadcn-based chat components (Conversation, Message, PromptInput, Response) via AI Elements
  - Standing up a "chat with your data" / RAG answer UI on top of the AI Gateway or a provider SDK
when_not_to_use:
  - Static or form UI with no model streaming — use frontend-ui-engineering
  - Net-new visual/brand direction for the page — use frontend-design
  - Only the server-side Anthropic model plumbing, no front-end — use claude-api
  - The core deliverable is charts/dashboards, not chat — use dataviz
keywords:
  - vercel ai sdk
  - usechat
  - generative ui
  - streaming chat
  - chatbot
  - ai elements
  - streamtext
  - react
  - nextjs
  - defaultchattransport
  - message parts
  - rag ui
  - copilot
  - assistant
  - tool calls
similar_to:
  - frontend-ui-engineering
  - frontend-design
  - web-artifacts-builder
inputs_needed: A React/Next.js (App Router) app, a provider API key or a Vercel AI Gateway key (AI_GATEWAY_API_KEY), and a model id.
produces: A working streaming chat UI — a client component using useChat plus a server route that streams UI messages back, optionally styled with AI Elements.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Generative UI Chat Interface (Vercel AI SDK v7 + AI Elements)

Stand up a production streaming chat front-end: a React client that renders tokens
as they stream, backed by a server route that calls the model. Verified against
`ai@7.x` and `@ai-sdk/react@7.x`.

## When to use

Any chat / assistant / copilot / RAG-answer surface that streams model output
token-by-token. For server-only Anthropic plumbing use `claude-api`; for non-chat
UI use `frontend-ui-engineering`.

## Prerequisites

- **Node 18+** and a React 18/19 app. Recipes assume **Next.js App Router**; the
  hook works in any React app pointed at any streaming endpoint.
- **Packages:** `npm i ai @ai-sdk/react` plus a provider — `@ai-sdk/openai`,
  `@ai-sdk/anthropic`, or use the built-in **Vercel AI Gateway** (pass a plain
  `'provider/model'` string and set `AI_GATEWAY_API_KEY`).
- **A key:** the provider key (e.g. `OPENAI_API_KEY`) or `AI_GATEWAY_API_KEY` — server-side only, never client-side.
- **AI Elements (optional):** requires an existing **shadcn/ui + Tailwind** setup.

> v7 API notes (these bite people migrating from v4/v5):
> - Render `message.parts`, **not** `message.content`.
> - `sendMessage({ text })` — no built-in `input`/`handleSubmit`; you own the input state.
> - Prompt field is `instructions` (`system` works but is deprecated).
> - `convertToModelMessages(...)` is **synchronous** — do not `await` it.
> - `result.toUIMessageStreamResponse()` works but is **deprecated**; prefer
>   `createUIMessageStreamResponse` + `toUIMessageStream` (Recipe 2).

## Recipe 1 — Client component (`app/page.tsx`)

```tsx
'use client';

import { useChat } from '@ai-sdk/react';
import { DefaultChatTransport } from 'ai';
import { useState } from 'react';

export default function Chat() {
  const { messages, sendMessage, status, stop, regenerate, error } = useChat({
    transport: new DefaultChatTransport({ api: '/api/chat' }),
  });
  const [input, setInput] = useState('');

  return (
    <div>
      {messages.map((message) => (
        <div key={message.id}>
          <strong>{message.role === 'user' ? 'You' : 'AI'}: </strong>
          {message.parts.map((part, i) =>
            part.type === 'text' ? <span key={i}>{part.text}</span> : null,
            // other part.type values: 'reasoning', 'tool-*', 'source-url', 'file'
          )}
        </div>
      ))}

      {error && (
        <p role="alert">
          Something went wrong. <button onClick={() => regenerate()}>Retry</button>
        </p>
      )}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          const text = input.trim();
          if (!text) return;
          sendMessage({ text });   // append the user message + trigger the stream
          setInput('');
        }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={status !== 'ready'}
          placeholder="Ask something…"
        />
        {status === 'submitted' || status === 'streaming' ? (
          <button type="button" onClick={() => stop()}>Stop</button>
        ) : (
          <button type="submit" disabled={!input.trim()}>Send</button>
        )}
      </form>
    </div>
  );
}
```

`status` is `'ready' | 'submitted' | 'streaming' | 'error'`. `useChat` also returns `setMessages`, `clearError`, `resumeStream`, `addToolResult`.

## Recipe 2 — Server route (`app/api/chat/route.ts`)

```ts
import {
  streamText,
  convertToModelMessages,
  createUIMessageStreamResponse,
  toUIMessageStream,
  type UIMessage,
} from 'ai';
import { openai } from '@ai-sdk/openai';

export const maxDuration = 30; // allow streaming beyond the default serverless timeout

export async function POST(req: Request) {
  const { messages }: { messages: UIMessage[] } = await req.json();

  const result = streamText({
    model: openai('gpt-4o'),        // or a gateway string: 'openai/gpt-4o'
    instructions: 'You are a concise, helpful assistant.',
    messages: convertToModelMessages(messages), // sync — no await
  });

  // Preferred v7 way to send a useChat-compatible stream:
  return createUIMessageStreamResponse({
    stream: toUIMessageStream({ stream: result.stream }),
  });
  // One-liner alt (deprecated, still works): return result.toUIMessageStreamResponse();
}
```

Swap providers via `model`: `anthropic('<model-id>')` from `@ai-sdk/anthropic`, or a
gateway string like `'anthropic/<model-id>'` — confirm the exact id from the provider,
don't guess. To stream reasoning too, pass `toUIMessageStream({ stream: result.stream, sendReasoning: true })`.

## Recipe 3 — Drop-in polished UI with AI Elements

AI Elements (`ai-elements@1.x`) is a shadcn-style registry — it copies component source
into `components/ai-elements/*.tsx` so you own and restyle it. Needs shadcn/ui + Tailwind.

```bash
npx ai-elements@latest                                       # install the full set
npx ai-elements@latest add conversation message prompt-input response  # or pick components
```

Compose them around the same `useChat` state:

```tsx
'use client';
import { useChat } from '@ai-sdk/react';
import { DefaultChatTransport } from 'ai';
import { useState } from 'react';
import { Conversation, ConversationContent } from '@/components/ai-elements/conversation';
import { Message, MessageContent } from '@/components/ai-elements/message';
import { Response } from '@/components/ai-elements/response';
import { PromptInput, PromptInputTextarea, PromptInputSubmit } from '@/components/ai-elements/prompt-input';

export default function Chat() {
  const { messages, sendMessage, status } = useChat({
    transport: new DefaultChatTransport({ api: '/api/chat' }),
  });
  const [input, setInput] = useState('');

  return (
    <div className="flex flex-col h-screen">
      <Conversation>
        <ConversationContent>
          {messages.map((m) => (
            <Message from={m.role} key={m.id}>
              <MessageContent>
                {m.parts.map((p, i) =>
                  p.type === 'text' ? <Response key={i}>{p.text}</Response> : null,
                )}
              </MessageContent>
            </Message>
          ))}
        </ConversationContent>
      </Conversation>

      <PromptInput
        onSubmit={(e) => {
          e.preventDefault();
          if (!input.trim()) return;
          sendMessage({ text: input });
          setInput('');
        }}
      >
        <PromptInputTextarea value={input} onChange={(e) => setInput(e.target.value)} />
        <PromptInputSubmit status={status} disabled={!input.trim()} />
      </PromptInput>
    </div>
  );
}
```

`Response` renders streamed Markdown safely. Other components: `Reasoning`, `Sources`,
`Suggestion`, `Loader`, `Task`, `Actions`.

## Verify

1. `npm run dev`, send a message — text appears **incrementally**, not one chunk. If it
   lands all at once the route isn't streaming (you returned `Response.json`, not the stream).
2. Network tab: `POST /api/chat` is `text/event-stream` and stays open.
3. Click **Stop** mid-stream → generation halts and `status` returns to `ready`.
4. Kill the key / return a 500 → `error` populates and the Retry path fires.
5. `npx tsc --noEmit` (or your build) is green — confirms the v7 imports resolve.

## Pitfalls

- **Blank messages / `.map is not a function`:** you rendered `message.content`. In v7
  it's `message.parts` (an array of typed parts).
- **`input`/`handleInputChange`/`handleSubmit` are undefined:** those v4 helpers were
  removed. Own the input `useState` and call `sendMessage({ text })` yourself.
- **`await convertToModelMessages(...)` throws / behaves oddly:** it's synchronous — drop the `await`.
- **Deprecation churn:** `system` → `instructions`; `result.toUIMessageStreamResponse()` →
  `createUIMessageStreamResponse` + `toUIMessageStream`. Old forms still run in v7 but warn.
- **Response ends after 10s on Vercel:** set `export const maxDuration = 30;` in the route.
- **Leaked API key:** keep provider/gateway keys server-side only; the client just hits `/api/chat`.
- **AI Elements import errors:** they require shadcn/ui + Tailwind configured and the `@/*` alias resolving.
- **Fabricated model ids 404 at request time:** confirm the exact provider model string from its docs.
