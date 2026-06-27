---
title: "Streams in Node: the only way to handle files bigger than RAM."
description: "Node.js streams process data incrementally. They are the right tool for large files, network data, and any situation where you can't load everything into memory."
pubDate: 2024-04-01
tags: ["Node.js"]
draft: false
---

The naive way to read a file in Node.js:

```js
const fs = require("fs");
const data = fs.readFileSync("huge-file.csv"); // Load the entire file into memory
```

For a 4GB file on a machine with 2GB of RAM, this crashes. Streams solve this by processing data in chunks, never holding the entire dataset in memory at once.

## What streams are

A stream is an abstract interface for working with streaming data. Node.js has four types:

- **Readable**: data you can read from (files, HTTP responses, stdin)
- **Writable**: data you can write to (files, HTTP requests, stdout)
- **Duplex**: both readable and writable (TCP sockets)
- **Transform**: a duplex that transforms data as it passes through (gzip compression)

## Reading a large file

```js
const fs = require("fs");

const stream = fs.createReadStream("large-file.csv", {
  encoding: "utf8",
  highWaterMark: 64 * 1024, // 64KB chunks
});

let lineCount = 0;
let remainder = "";

stream.on("data", (chunk) => {
  const lines = (remainder + chunk).split("\n");
  remainder = lines.pop(); // incomplete last line
  lineCount += lines.length;
});

stream.on("end", () => {
  if (remainder.length > 0) lineCount++;
  console.log(`Total lines: ${lineCount}`);
});

stream.on("error", (err) => {
  console.error("Stream error:", err);
});
```

The file is read in 64KB chunks. Memory usage stays constant regardless of file size.

## Piping streams

The cleanest way to use streams is `pipe`: connect a readable to a writable and let data flow automatically.

```js
const fs = require("fs");
const zlib = require("zlib");

const input = fs.createReadStream("large-file.txt");
const gzip = zlib.createGzip();
const output = fs.createWriteStream("large-file.txt.gz");

input.pipe(gzip).pipe(output);

output.on("finish", () => {
  console.log("Compression complete");
});
```

This compresses a file using constant memory, regardless of file size. Data flows: file → gzip transform → output file, chunk by chunk.

## pipeline: the safe version of pipe

`pipe` has a flaw: it does not forward errors between streams. If `gzip` errors, `output` does not close. Use `pipeline` instead:

```js
const { pipeline } = require("stream");
const fs = require("fs");
const zlib = require("zlib");

pipeline(
  fs.createReadStream("input.txt"),
  zlib.createGzip(),
  fs.createWriteStream("output.gz"),
  (err) => {
    if (err) {
      console.error("Pipeline failed:", err);
    } else {
      console.log("Pipeline succeeded");
    }
  }
);
```

`pipeline` properly handles errors and closes all streams when any stage fails.

## stream/promises for async/await

Node 15 added `stream/promises` for using pipeline with async/await:

```js
const { pipeline } = require("stream/promises");
const fs = require("fs");
const zlib = require("zlib");

async function compressFile(input, output) {
  await pipeline(
    fs.createReadStream(input),
    zlib.createGzip(),
    fs.createWriteStream(output)
  );
}
```

## Transform streams

Transform streams modify data as it passes through. A line-by-line CSV parser:

```js
const { Transform } = require("stream");

class CSVParser extends Transform {
  constructor() {
    super({ readableObjectMode: true }); // output objects, not buffers
    this._remainder = "";
    this._headers = null;
  }

  _transform(chunk, encoding, callback) {
    const lines = (this._remainder + chunk.toString()).split("\n");
    this._remainder = lines.pop();

    for (const line of lines) {
      if (!line.trim()) continue;

      if (!this._headers) {
        this._headers = line.split(",");
      } else {
        const values = line.split(",");
        const row = Object.fromEntries(
          this._headers.map((h, i) => [h, values[i]])
        );
        this.push(row); // push an object downstream
      }
    }

    callback();
  }

  _flush(callback) {
    if (this._remainder && this._headers) {
      const values = this._remainder.split(",");
      this.push(Object.fromEntries(
        this._headers.map((h, i) => [h, values[i]])
      ));
    }
    callback();
  }
}

// Usage:
pipeline(
  fs.createReadStream("data.csv"),
  new CSVParser(),
  new Writable({
    objectMode: true,
    write(row, _, cb) {
      console.log(row); // { name: "Alice", age: "30", ... }
      cb();
    }
  }),
  (err) => { if (err) console.error(err); }
);
```

## Backpressure

Streams handle backpressure automatically. If the consumer (writable) is slower than the producer (readable), the readable pauses itself until the writable is ready. `pipe` and `pipeline` manage this for you.

If you are manually writing to a writable stream:

```js
const canContinue = writable.write(chunk);
if (!canContinue) {
  readable.pause(); // stop reading until writable drains
  writable.once("drain", () => {
    readable.resume();
  });
}
```

For most use cases, `pipeline` handles this automatically.

## When to use streams

Use streams when:
- The data is too large to fit comfortably in memory
- You want to start processing before all data is available (lower latency)
- You are proxying data between two endpoints (HTTP proxy, file copy)

For small files (under a few MB), `fs.readFile` is simpler and perfectly acceptable. Streams are the tool for data at scale.
