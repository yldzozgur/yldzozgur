---
title: "Text-to-speech: latency, voice selection, and streaming audio back."
description: "How TTS APIs work, how to pick voices, and how to stream audio to the client before the full synthesis is done."
pubDate: 2025-05-08
tags: ["AI", "Speech"]
draft: false
---

Text-to-speech has gone from robotic to surprisingly natural in a short time. OpenAI's TTS API and ElevenLabs are the two most commonly integrated options. Understanding how they work under the hood changes how you design around them.

## How synthesis works

You send text, you get back audio. That is the basic model. But the latency profile depends on whether the API streams or buffers.

In a non-streaming call, the provider synthesizes the entire audio clip server-side, then returns it as a complete blob. For a 200-word paragraph, that might be 10-15 seconds of audio. The API call itself takes 2-4 seconds, then you download the file.

In a streaming call, the provider starts returning audio chunks before synthesis is complete. The first chunk might arrive in under a second. Your application can start playing audio while the rest is still being generated.

For anything involving user-facing voice output in real time, streaming is not optional.

## OpenAI TTS

```javascript
import OpenAI from "openai";
import fs from "fs";

const client = new OpenAI();

// Non-streaming, save to file
const response = await client.audio.speech.create({
  model: "tts-1",
  voice: "alloy",
  input: "The deployment finished successfully.",
  response_format: "mp3"
});

const buffer = Buffer.from(await response.arrayBuffer());
fs.writeFileSync("output.mp3", buffer);
```

For streaming:

```javascript
const response = await client.audio.speech.create({
  model: "tts-1",
  voice: "nova",
  input: "Starting synthesis now.",
  response_format: "pcm" // raw PCM is lowest latency
});

// response.body is a ReadableStream
for await (const chunk of response.body) {
  audioPlayer.write(chunk); // write chunks to your audio pipeline
}
```

OpenAI offers two models: `tts-1` (lower latency, slightly lower quality) and `tts-1-hd` (higher quality, more latency). For real-time voice use cases, `tts-1` is usually the right choice.

## Voice selection

OpenAI provides six voices: `alloy`, `echo`, `fable`, `onyx`, `nova`, `shimmer`. They are differentiated by pitch and tone. There is no gender tagging in the API; you pick by listening.

A few practical observations:
- `nova` and `shimmer` are lighter, higher-pitched
- `onyx` is deeper
- `alloy` and `echo` sit in the middle

ElevenLabs offers a much larger voice library, including cloned voices, multilingual voices, and fine-grained emotion controls. The tradeoff is higher per-character cost and more API surface to manage.

## Audio format and latency

The response format affects first-byte latency and file size:

| Format | Notes |
|--------|-------|
| `mp3` | Compressed, good for file storage |
| `opus` | Best for streaming, low latency codec |
| `aac` | Good mobile compatibility |
| `flac` | Lossless, large |
| `pcm` | Raw samples, no codec overhead, lowest latency |
| `wav` | PCM with a header |

For browser playback over WebSocket, `pcm` with 16kHz 16-bit mono is a common choice. You handle buffering yourself, but there is zero codec overhead on the synthesis side.

## Streaming to the browser

A typical server-side route that streams TTS audio:

```javascript
// Express route
app.post("/speak", async (req, res) => {
  const { text } = req.body;

  res.setHeader("Content-Type", "audio/mpeg");
  res.setHeader("Transfer-Encoding", "chunked");

  const ttsResponse = await client.audio.speech.create({
    model: "tts-1",
    voice: "alloy",
    input: text,
    response_format: "mp3"
  });

  for await (const chunk of ttsResponse.body) {
    res.write(chunk);
  }

  res.end();
});
```

On the client, use the Fetch API with a `ReadableStream` to start playing before the response completes:

```javascript
const response = await fetch("/speak", {
  method: "POST",
  body: JSON.stringify({ text }),
  headers: { "Content-Type": "application/json" }
});

const reader = response.body.getReader();
const audioContext = new AudioContext();
// ... decode and play chunks
```

Web Audio API decoding of streaming MP3 is non-trivial because MP3 frames need to be aligned. The cleanest approach is to accumulate chunks into a buffer and decode in larger segments, or switch to `pcm` format where you can play raw samples directly.

## Chunking long text

TTS APIs have input length limits (OpenAI: 4096 characters). For longer content, split on sentence boundaries before sending:

```javascript
function splitSentences(text, maxChars = 500) {
  const sentences = text.match(/[^.!?]+[.!?]+/g) ?? [text];
  const chunks = [];
  let current = "";

  for (const sentence of sentences) {
    if ((current + sentence).length > maxChars) {
      if (current) chunks.push(current.trim());
      current = sentence;
    } else {
      current += sentence;
    }
  }
  if (current) chunks.push(current.trim());
  return chunks;
}
```

Process chunks in order, piping each response to your audio pipeline before requesting the next. This keeps latency low for the first audible output while the rest generates in a rolling fashion.
