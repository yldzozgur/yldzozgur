---
title: "Chunking audio for transcription: size, overlap, and the timing that matters."
description: "The Whisper API has a 25MB file size limit. For long recordings, chunking is required. How to split audio correctly so transcription quality doesn't suffer at the boundaries."
pubDate: 2025-04-17
tags: ["AI", "OpenAI", "Audio", "Whisper"]
draft: false
---

## Why chunking is necessary

The Whisper API accepts a maximum of 25MB per request. A 25MB MP3 at 128kbps is roughly 27 minutes. For longer recordings -- interviews, lectures, meetings -- you need to split the audio into chunks and transcribe each one.

Naive splitting (cut every N minutes) creates problems at the boundaries: words get cut in half, sentences lose context, and the model may hallucinate completions at the end of a chunk because the audio terminates abruptly.

## Calculating chunk size

For safety, target chunks well under the 25MB limit. At common audio bitrates:

| Format | Bitrate | 10 minutes |
|--------|---------|------------|
| MP3 | 128kbps | ~9.6 MB |
| MP3 | 64kbps | ~4.8 MB |
| m4a | 64kbps | ~4.8 MB |
| wav | 16kHz mono | ~19.2 MB |

For MP3 at 128kbps, 10-minute chunks leave comfortable headroom. For high-quality WAV, 5-minute chunks are safer.

## Splitting with ffmpeg

`ffmpeg` is the standard tool for audio manipulation:

```bash
# Split into 10-minute segments with 10-second overlap
ffmpeg -i input.mp3 \
  -f segment \
  -segment_time 600 \
  -segment_start_number 0 \
  -c copy \
  chunk_%03d.mp3
```

The `-segment_time 600` sets the chunk length in seconds. `-c copy` copies the audio stream without re-encoding, which is fast and lossless.

In Node.js with `fluent-ffmpeg`:

```javascript
const ffmpeg = require('fluent-ffmpeg');
const path = require('path');

function splitAudio(inputPath, outputDir, chunkDurationSeconds = 600) {
  return new Promise((resolve, reject) => {
    ffmpeg(inputPath)
      .outputOptions([
        '-f segment',
        `-segment_time ${chunkDurationSeconds}`,
        '-c copy',
        '-reset_timestamps 1',
      ])
      .output(path.join(outputDir, 'chunk_%03d.mp3'))
      .on('end', resolve)
      .on('error', reject)
      .run();
  });
}
```

## The overlap problem

When you split audio at exact time boundaries, the last word in a chunk may be cut off. The transcription model receives audio that ends mid-word or mid-sentence, which degrades accuracy.

**Overlap** solves this: each chunk includes a few seconds of the previous chunk's content. When you combine the transcriptions, you match the overlapping text and merge at the overlap point.

```javascript
async function transcribeWithOverlap(inputPath, overlapSeconds = 5) {
  const chunks = await splitWithOverlap(inputPath, 600, overlapSeconds);
  const transcriptions = [];

  for (const chunk of chunks) {
    const result = await openai.audio.transcriptions.create({
      file: fs.createReadStream(chunk.path),
      model: 'whisper-1',
      response_format: 'verbose_json',
      timestamp_granularities: ['segment'],
    });
    transcriptions.push({ ...result, startOffset: chunk.startOffset });
  }

  return mergeTranscriptions(transcriptions, overlapSeconds);
}
```

## Merging overlapping transcriptions

After transcribing overlapping chunks, remove the duplicated content at boundaries:

```javascript
function mergeTranscriptions(transcriptions, overlapSeconds) {
  let merged = transcriptions[0].text;

  for (let i = 1; i < transcriptions.length; i++) {
    const prev = transcriptions[i - 1];
    const curr = transcriptions[i];

    // Find the overlap region in both transcriptions
    const overlapStart = prev.duration - overlapSeconds;

    // Get text from the overlap region in the previous transcription
    const overlapSegments = prev.segments.filter(s => s.start >= overlapStart);
    const overlapText = overlapSegments.map(s => s.text.trim()).join(' ');

    // Find where the overlap text appears in the current transcription
    const overlapIndex = curr.text.indexOf(overlapText.slice(0, 30));

    if (overlapIndex > -1) {
      merged += curr.text.slice(overlapIndex + overlapText.length);
    } else {
      // Fallback: no clean overlap found, just append
      merged += ' ' + curr.text;
    }
  }

  return merged;
}
```

## Silence detection for natural splits

Better than fixed-time splits: split at natural pause points. `ffmpeg` can detect silence:

```bash
ffmpeg -i input.mp3 -af silencedetect=noise=-30dB:d=0.5 -f null - 2>&1 | grep silence
```

This outputs timestamps where audio is quiet for at least 0.5 seconds at -30dB. Split at these natural boundaries to avoid cutting words in half. Each chunk ends at a pause, which is where speakers naturally complete thoughts.

Implementing this in code requires parsing `ffmpeg`'s stderr output and then making split decisions based on the silence timestamps. The result is cleaner transcriptions at boundaries because each chunk starts after a natural pause.
