---
title: "WebAssembly: running near-native code in the browser."
description: "How WebAssembly works, how to compile Rust and C to Wasm, and when it makes sense to reach for it."
pubDate: 2025-11-20
tags: ["JavaScript", "Performance"]
draft: false
---

JavaScript is interpreted (or JIT-compiled), runs in a single thread, and has overhead from dynamic typing. For most web applications, this is fine. For computation-intensive tasks -- image processing, video encoding, cryptography, scientific simulations -- JavaScript can be 10-100x slower than native code. WebAssembly is the standard that brings near-native performance to the browser.

## What WebAssembly is

WebAssembly (Wasm) is a binary instruction format for a stack-based virtual machine. Browsers can execute Wasm natively, close to the speed of machine code, because:

- It's statically typed (no dynamic dispatch overhead)
- It's compiled ahead of time (no JIT warmup)
- It maps directly to low-level CPU instructions

You don't write WebAssembly directly. You compile to it from languages like C, C++, or Rust.

## Compiling Rust to WebAssembly

Rust has first-class WebAssembly support through `wasm-pack`:

```bash
cargo install wasm-pack
cargo new --lib image-processor
cd image-processor
```

`Cargo.toml`:

```toml
[lib]
crate-type = ["cdylib"]

[dependencies]
wasm-bindgen = "0.2"
image = "0.25"
```

`src/lib.rs`:

```rust
use wasm_bindgen::prelude::*;

#[wasm_bindgen]
pub fn grayscale(data: &[u8], width: u32, height: u32) -> Vec<u8> {
    let mut output = vec![0u8; (width * height * 4) as usize];
    
    for i in (0..data.len()).step_by(4) {
        let r = data[i] as f32;
        let g = data[i + 1] as f32;
        let b = data[i + 2] as f32;
        let gray = (0.299 * r + 0.587 * g + 0.114 * b) as u8;
        
        output[i] = gray;
        output[i + 1] = gray;
        output[i + 2] = gray;
        output[i + 3] = data[i + 3]; // preserve alpha
    }
    
    output
}
```

Build:

```bash
wasm-pack build --target web
```

This produces a `pkg/` directory with the Wasm binary and JavaScript bindings.

## Using Wasm from JavaScript

```javascript
import init, { grayscale } from "./pkg/image_processor.js";

await init(); // Load the Wasm module

const canvas = document.getElementById("canvas");
const ctx = canvas.getContext("2d");
const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);

// Pass pixel data to Wasm, get back processed data
const grayData = grayscale(imageData.data, canvas.width, canvas.height);

const newImageData = new ImageData(
  new Uint8ClampedArray(grayData),
  canvas.width,
  canvas.height
);
ctx.putImageData(newImageData, 0, 0);
```

The `grayscale` function runs in Wasm at native speed. For a 4K image (8.3 million pixels), this is significantly faster than an equivalent JavaScript implementation.

## Memory model

Wasm has its own linear memory, separate from the JavaScript heap. Passing data between JavaScript and Wasm involves copying across this boundary, which has overhead.

For performance-critical code, minimize boundary crossings:

```javascript
// Bad: many small transfers
for (const pixel of pixels) {
  const result = wasmModule.processPixel(pixel);
}

// Good: one large transfer
const result = wasmModule.processAllPixels(pixels); // process in bulk
```

For very large data, use shared memory (`SharedArrayBuffer`) to avoid copying entirely:

```javascript
const sharedBuffer = new SharedArrayBuffer(imageData.data.byteLength);
const sharedArray = new Uint8Array(sharedBuffer);
sharedArray.set(imageData.data); // Copy once

// Pass shared memory reference to Wasm
wasmModule.processInPlace(sharedArray);
// No copy back needed - Wasm modified the shared buffer
```

## Existing Wasm projects to use today

You don't always need to write Wasm from scratch. Many established libraries are compiled to Wasm:

**FFmpeg.wasm**: Video and audio processing in the browser:

```javascript
import { FFmpeg } from "@ffmpeg/ffmpeg";

const ffmpeg = new FFmpeg();
await ffmpeg.load();

await ffmpeg.writeFile("input.mp4", await fetchFile(videoFile));
await ffmpeg.exec(["-i", "input.mp4", "-ss", "00:00:01", "-t", "5", "output.mp4"]);
const data = await ffmpeg.readFile("output.mp4");
```

**SQLite.wasm**: Full SQLite database in the browser, from the SQLite project itself.

**OpenCV.js**: Computer vision algorithms at near-native speed.

**Argon2-browser**: Password hashing with the intentionally slow Argon2 algorithm.

## When to use WebAssembly

WebAssembly has real overhead: loading the Wasm binary, initializing the module, and crossing the JS/Wasm boundary. It makes sense when:

- **Heavy computation**: Image/video processing, audio synthesis, scientific computing, cryptography
- **Existing C/C++/Rust library**: A battle-tested library in another language that you want to use without rewriting
- **Predictable performance**: Wasm doesn't have GC pauses (unless you're using Wasm GC for garbage-collected languages)

It does not make sense for:
- Simple data transformation
- UI code that touches the DOM (Wasm can't touch the DOM directly without JS bridge calls)
- Code that needs to be modified frequently (Rust compile times are long)

The typical pattern is a JavaScript orchestrator that handles UI and coordination, calling into Wasm for the heavy lifting. The boundary between the two is where you should spend time optimizing.
