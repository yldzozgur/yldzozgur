---
title: "MCP: the protocol that lets AI models use tools."
description: "What the Model Context Protocol is, how it works, and how to build an MCP server that exposes tools to AI models."
pubDate: 2025-09-01
tags: ["DevOps"]
draft: false
---

AI models are more useful when they can take actions - search the web, read files, query databases, call APIs. The challenge is that every application that embeds an AI model needs to implement its own tool integration layer. MCP (Model Context Protocol) is a standardized protocol that defines how models communicate with external tools, so that tools built once work with any MCP-compatible model client.

## What MCP is

MCP is a client-server protocol where:
- The **client** is an AI model host (a coding assistant, a chat application, an agent runtime)
- The **server** is a process that exposes tools, resources, or prompts

The client connects to one or more MCP servers. The model can discover available tools from connected servers and invoke them during inference. The server implements the tools and returns results.

This is analogous to how an operating system provides a standard system call interface - applications do not need to know the hardware details, they just call the interface. MCP provides a standard tool interface that model clients and tool providers can both implement without coordinating directly.

## The transport

MCP supports two transports: stdio (for local tools, the server is a child process) and HTTP with Server-Sent Events (for remote tools).

Stdio transport is the simplest to implement. The client spawns the server as a subprocess and communicates over stdin/stdout using JSON-RPC messages.

## Building an MCP server

A minimal MCP server in Python using the official SDK:

```python
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import mcp.types as types

server = Server("my-tools")

@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="read_file",
            description="Read the contents of a file",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to read"
                    }
                },
                "required": ["path"]
            }
        ),
        Tool(
            name="search_web",
            description="Search the web for information",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "num_results": {"type": "integer", "default": 5}
                },
                "required": ["query"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "read_file":
        path = arguments["path"]
        with open(path, 'r') as f:
            content = f.read()
        return [TextContent(type="text", text=content)]
    
    elif name == "search_web":
        results = await web_search(arguments["query"], arguments.get("num_results", 5))
        return [TextContent(type="text", text=format_results(results))]
    
    raise ValueError(f"Unknown tool: {name}")

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

import asyncio
asyncio.run(main())
```

## Resources and prompts

MCP servers can expose three types of things:

**Tools** - Functions the model can call. The model decides when to call them based on the task. The examples above are tools.

**Resources** - Data sources the client can read. Think of these as files or data streams the model can access. A resource might be a database connection, a file system path, or a live data feed.

```python
@server.list_resources()
async def list_resources():
    return [
        types.Resource(
            uri="db://customers/recent",
            name="Recent Customers",
            mimeType="application/json"
        )
    ]

@server.read_resource()
async def read_resource(uri: str):
    if uri == "db://customers/recent":
        customers = await db.fetch_recent_customers()
        return json.dumps(customers)
```

**Prompts** - Pre-written prompt templates the client can use. These let tool developers ship curated prompts alongside their tools.

## Connecting an MCP server to a client

In Claude Desktop, add the server to the configuration:

```json
{
  "mcpServers": {
    "my-tools": {
      "command": "python",
      "args": ["/path/to/my_server.py"],
      "env": {
        "API_KEY": "..."
      }
    }
  }
}
```

Programmatically, using the MCP client SDK:

```typescript
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

const transport = new StdioClientTransport({
  command: "python",
  args: ["my_server.py"],
});

const client = new Client({ name: "my-client", version: "1.0.0" });
await client.connect(transport);

const tools = await client.listTools();
const result = await client.callTool({ name: "read_file", arguments: { path: "/tmp/data.txt" } });
```

## Why the standardization matters

Before MCP, every AI coding assistant, every agent framework, and every AI application implemented its own tool interface. A Slack integration built for one framework did not work with another. MCP creates a common protocol so a tool server built once can work with Claude Desktop, Cursor, any agent SDK that implements the client side.

The ecosystem effect is the value: the more clients implement MCP, the more useful each individual MCP server becomes. Build a database query tool once. Every MCP-compatible client can use it.
