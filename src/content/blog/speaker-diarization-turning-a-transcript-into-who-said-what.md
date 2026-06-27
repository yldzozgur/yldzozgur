---
title: "Speaker diarization: turning a transcript into 'who said what.'"
description: "Transcription gives you text. Diarization adds speaker identity. How diarization works, the tools available, and how to combine it with Whisper output."
pubDate: 2025-04-21
tags: ["AI", "Audio", "Whisper"]
draft: false
---

## What diarization is

A transcript from Whisper is a sequence of words with timestamps. It doesn't know how many speakers are in the recording or which words each speaker said.

Diarization answers the question: "at time T, which speaker is talking?" The output is a set of time-stamped segments labeled with speaker IDs (Speaker 1, Speaker 2, etc.). Combined with a word-level Whisper transcript, you get a complete picture of who said what and when.

## How diarization works

Diarization models use audio embeddings -- numerical representations of voice characteristics -- to identify clusters of similar voice segments. The process:

1. Split the audio into short segments (typically 1-3 seconds)
2. Compute a voice embedding for each segment
3. Cluster segments by embedding similarity
4. Each cluster becomes a "speaker"

Modern models do this well for 2-4 speakers in clean audio. Performance degrades with many speakers, overlapping speech, or noisy environments.

## pyannote.audio

The open-source standard for diarization is `pyannote.audio`. It's a Python library with a Hugging Face-hosted model.

```python
from pyannote.audio import Pipeline

pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-3.1",
    use_auth_token="your_hf_token"
)

diarization = pipeline("interview.mp3")

for turn, _, speaker in diarization.itertracks(yield_label=True):
    print(f"{turn.start:.1f}s - {turn.end:.1f}s: {speaker}")
    # 0.0s - 2.3s: SPEAKER_00
    # 2.3s - 5.1s: SPEAKER_01
    # 5.1s - 8.7s: SPEAKER_00
```

The output is a series of time segments, each assigned to a speaker label.

## Combining diarization with Whisper

The standard pipeline:

1. Transcribe with Whisper (verbose_json, word timestamps)
2. Diarize with pyannote
3. For each word timestamp, find which speaker segment it falls in
4. Assign the speaker label to the word

```python
import json
from openai import OpenAI

client = OpenAI()

# Step 1: Transcribe
with open("interview.mp3", "rb") as f:
    transcription = client.audio.transcriptions.create(
        file=f,
        model="whisper-1",
        response_format="verbose_json",
        timestamp_granularities=["word"]
    )

# Step 2: Diarize (assumes diarization is done separately)
# diarization segments from pyannote: [{start, end, speaker}, ...]

# Step 3: Assign speakers to words
def get_speaker_at(time, diarization_segments):
    for seg in diarization_segments:
        if seg['start'] <= time <= seg['end']:
            return seg['speaker']
    return 'UNKNOWN'

labeled_words = []
for word in transcription.words:
    midpoint = (word['start'] + word['end']) / 2
    speaker = get_speaker_at(midpoint, diarization_segments)
    labeled_words.append({
        'word': word['word'],
        'start': word['start'],
        'end': word['end'],
        'speaker': speaker,
    })
```

## Formatting the output

Group consecutive words by the same speaker into utterances:

```python
def group_by_speaker(labeled_words):
    utterances = []
    current = None

    for word in labeled_words:
        if current is None or word['speaker'] != current['speaker']:
            if current:
                utterances.append(current)
            current = {
                'speaker': word['speaker'],
                'start': word['start'],
                'end': word['end'],
                'text': word['word'],
            }
        else:
            current['text'] += word['word']
            current['end'] = word['end']

    if current:
        utterances.append(current)

    return utterances
```

Output:

```
[00:00 - 00:05] SPEAKER_00: "Welcome to the podcast, glad to have you here."
[00:05 - 00:12] SPEAKER_01: "Thanks for having me, excited to be here."
```

## API services

If running Python models isn't an option, several APIs offer combined transcription + diarization:

- **AssemblyAI**: `speaker_labels: true` parameter
- **Deepgram**: `diarize=true` parameter
- **Gladia**: transcription with diarization in one call

These services run both steps and return a combined response, avoiding the need to merge two outputs manually.

## Limitations

Speaker diarization is not perfect. Overlapping speech is difficult -- most models pick one speaker for overlapping segments. Speaker count must be estimated or configured. Very short utterances (under 1 second) may be misassigned. For production applications, consider letting users correct speaker labels manually.
