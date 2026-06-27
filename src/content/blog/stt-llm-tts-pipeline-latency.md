---
title: "STT to LLM to TTS: a pipeline where every hop adds latency."
description: "How to architect a speech-to-speech pipeline and where to optimize each stage to minimize end-to-end latency."
pubDate: 2025-05-12
tags: ["AI", "Speech"]
draft: false
---

A voice AI pipeline has three stages: speech-to-text converts audio to a transcript, an LLM generates a response, text-to-speech converts that response back to audio. Each hop adds latency. Understanding where time goes is the first step to reducing it.

## The baseline numbers

A reasonable baseline for each stage on current cloud APIs:

| Stage | Latency |
|-------|---------|
| STT (Whisper API, ~5s audio) | 500-1200ms |
| LLM (GPT-4o, first token) | 300-800ms |
| LLM (full response, 50 tokens) | 1-3s |
| TTS (first audio chunk, streaming) | 200-600ms |

End-to-end before the user hears anything: roughly 1-3 seconds if you stream and overlap. If you wait for complete outputs at each stage, you're looking at 4-8 seconds.

## The naive sequential implementation

```javascript
// Don't do this for real-time voice
async function voicePipelineNaive(audioBlob) {
  // Stage 1: STT
  const transcript = await transcribe(audioBlob);

  // Stage 2: LLM - wait for complete response
  const llmResponse = await generateFullResponse(transcript);

  // Stage 3: TTS - wait for complete audio
  const audioBuffer = await synthesize(llmResponse);

  return audioBuffer; // 5-8 seconds later
}
```

This is the worst possible approach for latency. Every stage waits for the previous to fully complete.

## Streaming overlap: the key optimization

The core insight is that you can start TTS before the LLM finishes. As tokens stream out of the LLM, you accumulate them into sentence-sized chunks and send each chunk to TTS immediately.

```javascript
async function voicePipelineStreaming(audioBlob) {
  // Stage 1: STT (must complete before LLM can start)
  const transcript = await transcribe(audioBlob);

  // Stage 2+3: LLM streams, TTS starts on first sentence
  const llmStream = await client.chat.completions.create({
    model: "gpt-4o",
    messages: [{ role: "user", content: transcript }],
    stream: true
  });

  let buffer = "";
  const audioQueue = [];

  for await (const chunk of llmStream) {
    const token = chunk.choices[0]?.delta?.content ?? "";
    buffer += token;

    // Flush on sentence boundary
    if (/[.!?]\s/.test(buffer) && buffer.length > 20) {
      const sentence = buffer.trim();
      buffer = "";
      // Don't await — queue TTS requests concurrently
      audioQueue.push(synthesizeAndPlay(sentence));
    }
  }

  // Flush remainder
  if (buffer.trim()) audioQueue.push(synthesizeAndPlay(buffer.trim()));
  await Promise.all(audioQueue);
}
```

The first TTS request fires the moment the LLM produces its first sentence. The user starts hearing audio 1-2 seconds after they stop speaking, rather than 5-8.

## The sentence boundary problem

Splitting on `. ` is fragile. "Dr. Smith said..." will split incorrectly. A minimal fix:

```javascript
function flushOnSentence(buffer) {
  // Only split on period followed by space and lowercase start
  // to avoid splitting on abbreviations
  const match = buffer.match(/^(.+?[!?]|.+?\.\s+(?=[A-Z]))/);
  if (match && match[0].length > 15) {
    return {
      chunk: match[0].trim(),
      remainder: buffer.slice(match[0].length)
    };
  }
  return null;
}
```

For production, a small NLP sentence tokenizer is worth the dependency.

## STT: streaming vs batch

Whisper (via OpenAI API) is a batch model. You send audio, you get text. There is no word-by-word streaming from the current hosted API.

For lower STT latency, options include:
- **Deepgram Nova-2**: streaming STT with word-level timestamps and ~200ms latency
- **AssemblyAI**: streaming with similar latency
- **Whisper self-hosted**: remove the network hop, run locally

Deepgram's streaming API uses WebSockets:

```javascript
const { createClient, LiveTranscriptionEvents } = require("@deepgram/sdk");
const deepgram = createClient(process.env.DEEPGRAM_API_KEY);

const connection = deepgram.listen.live({ model: "nova-2", smart_format: true });

connection.on(LiveTranscriptionEvents.Transcript, (data) => {
  const words = data.channel.alternatives[0].transcript;
  if (data.is_final && words) {
    onTranscript(words);
  }
});
```

With streaming STT, you can detect when the user stops speaking (voice activity detection) and start the LLM call before they have fully finished. This overlaps STT and LLM processing.

## Interruption handling

Real voice conversations have interruptions. The user starts talking while the AI is still speaking. Your pipeline needs:

1. Voice activity detection (VAD) to detect when the user speaks
2. Cancellation of any in-flight LLM or TTS requests
3. Clearing of the audio playback queue
4. Starting a new pipeline cycle immediately

```javascript
vadStream.on("speech_start", () => {
  // Cancel ongoing generation
  currentLLMController?.abort();
  audioPlayer.flush(); // clear queued audio
  startNewCycle();
});
```

The `AbortController` pattern works well for canceling in-flight fetch requests to both LLM and TTS APIs.

## Choosing a TTS model for real-time

OpenAI's `tts-1` model targets lower latency at the cost of some audio quality. ElevenLabs has a "Flash" tier designed for streaming with sub-400ms first-chunk latency. For telephony, dedicated providers like Deepgram's Aura or Amazon Polly Neural are optimized for the audio formats phone systems expect.

The best end-to-end latency currently achievable with cloud APIs: roughly 800ms to first audio. With self-hosted STT and a small LLM, you can push below 500ms. The pipeline architecture matters more than any individual component.
