---
title: "OpenAI Whisper API: what the response actually looks like and how to use it."
description: "A practical look at the Whisper transcription API response format, the verbose JSON mode with timestamps, and how to use the output in real applications."
pubDate: 2025-04-14
tags: ["AI", "OpenAI", "Audio", "Whisper"]
draft: false
---

## The basic transcription call

Whisper is OpenAI's speech-to-text model. The API takes an audio file and returns text.

```javascript
import OpenAI from 'openai';
import fs from 'fs';

const openai = new OpenAI();

const transcription = await openai.audio.transcriptions.create({
  file: fs.createReadStream('audio.mp3'),
  model: 'whisper-1',
});

console.log(transcription.text);
// "The quick brown fox jumps over the lazy dog."
```

The default response is a single `text` field with the complete transcription. Simple and fast for most use cases.

## Accepted audio formats

Whisper accepts: mp3, mp4, mpeg, mpga, m4a, wav, webm. The maximum file size is 25MB.

For React Native audio recordings (usually m4a), the format works directly. For WebRTC recordings (webm), it also works.

## The verbose JSON response

For applications that need more than raw text, the `verbose_json` response format returns word-level and segment-level data including timestamps.

```javascript
const transcription = await openai.audio.transcriptions.create({
  file: fs.createReadStream('audio.mp3'),
  model: 'whisper-1',
  response_format: 'verbose_json',
  timestamp_granularities: ['word', 'segment'],
});
```

The response structure:

```json
{
  "text": "The quick brown fox jumps over the lazy dog.",
  "task": "transcribe",
  "language": "english",
  "duration": 3.24,
  "segments": [
    {
      "id": 0,
      "seek": 0,
      "start": 0.0,
      "end": 3.24,
      "text": " The quick brown fox jumps over the lazy dog.",
      "tokens": [50364, 440, 1702, 6292, 21831, ...],
      "temperature": 0.0,
      "avg_logprob": -0.23,
      "compression_ratio": 1.38,
      "no_speech_prob": 0.08
    }
  ],
  "words": [
    { "word": "The", "start": 0.0, "end": 0.18 },
    { "word": "quick", "start": 0.18, "end": 0.38 },
    { "word": "brown", "start": 0.38, "end": 0.62 },
    ...
  ]
}
```

## What to do with word timestamps

Word-level timestamps enable several features:

**Karaoke-style highlighting**: as audio plays back, highlight the current word being spoken using the `start` and `end` times.

**Clickable transcripts**: click a word to seek the audio player to that position.

**Accurate subtitle generation**: split the transcript into subtitle blocks using segment boundaries.

```javascript
function createSubtitles(words, maxWordsPerLine = 8) {
  const subtitles = [];
  let current = [];

  for (const word of words) {
    current.push(word);
    if (current.length >= maxWordsPerLine) {
      subtitles.push({
        start: current[0].start,
        end: current[current.length - 1].end,
        text: current.map(w => w.word).join(' '),
      });
      current = [];
    }
  }

  if (current.length > 0) {
    subtitles.push({
      start: current[0].start,
      end: current[current.length - 1].end,
      text: current.map(w => w.word).join(' '),
    });
  }

  return subtitles;
}
```

## Language detection and specification

Whisper detects the language automatically. The response includes a `language` field with the detected language.

For better accuracy when you know the language in advance:

```javascript
const transcription = await openai.audio.transcriptions.create({
  file: fs.createReadStream('audio.mp3'),
  model: 'whisper-1',
  language: 'en', // ISO 639-1 language code
});
```

Specifying the language is faster and more accurate, especially for short clips where auto-detection might get it wrong.

## Translation

Whisper can translate audio from any supported language into English:

```javascript
const translation = await openai.audio.translations.create({
  file: fs.createReadStream('spanish_audio.mp3'),
  model: 'whisper-1',
});

console.log(translation.text);
// English translation of the Spanish audio
```

The translation endpoint always outputs English. For other target languages, you'd use the transcription API to get text in the original language, then translate with a language model.

## Error handling

The main failure modes are file size (>25MB), unsupported format, and corrupted audio. The API throws standard errors that include the failure reason. Implement retry logic for transient errors:

```javascript
async function transcribeWithRetry(filePath, maxRetries = 3) {
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await openai.audio.transcriptions.create({
        file: fs.createReadStream(filePath),
        model: 'whisper-1',
      });
    } catch (error) {
      if (attempt === maxRetries - 1) throw error;
      await new Promise(resolve => setTimeout(resolve, 1000 * (attempt + 1)));
    }
  }
}
```
