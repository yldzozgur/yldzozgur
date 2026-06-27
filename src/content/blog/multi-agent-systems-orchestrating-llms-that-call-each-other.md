---
title: "Multi-agent systems: orchestrating LLMs that call each other."
description: "What multi-agent LLM systems are, the patterns for structuring them, and the practical challenges of building reliable agent pipelines."
pubDate: 2025-08-28
tags: ["DevOps"]
draft: false
---

A single LLM call handles a bounded task: answer a question, summarize a document, generate code. Complex workflows exceed what a single call can do well - not because of context limits, but because they require multiple distinct capabilities, parallel execution, iterative refinement, or specialized models for different subtasks. Multi-agent systems address this by composing multiple LLM calls into a coordinated pipeline.

## The orchestrator-worker pattern

The most common multi-agent structure has an orchestrator that receives a goal, breaks it into tasks, and delegates tasks to specialized worker agents.

```python
async def research_assistant(topic: str) -> str:
    # Orchestrator decides what workers to call
    outline = await call_llm(
        system="You are a research planner. Break the topic into 3-5 subtopics to investigate.",
        user=f"Research topic: {topic}"
    )
    
    subtopics = parse_outline(outline)
    
    # Workers run in parallel
    research_tasks = [
        research_subtopic(subtopic) for subtopic in subtopics
    ]
    results = await asyncio.gather(*research_tasks)
    
    # Synthesizer combines results
    synthesis = await call_llm(
        system="You are a research synthesizer. Write a cohesive report from these research findings.",
        user="\n\n".join(results)
    )
    
    return synthesis

async def research_subtopic(subtopic: str) -> str:
    # This worker could use RAG, web search, or other tools
    search_results = await web_search(subtopic)
    return await call_llm(
        system="Summarize the key findings from these search results.",
        user=f"Subtopic: {subtopic}\n\nResults: {search_results}"
    )
```

Each worker is focused and bounded. The orchestrator handles coordination. The synthesizer handles combining output.

## Tool-using agents

Agents become more powerful when they can take actions, not just generate text. Tools are functions the model can call:

```python
tools = [
    {
        "name": "search_docs",
        "description": "Search the documentation for relevant information",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"}
            }
        }
    },
    {
        "name": "run_code",
        "description": "Execute Python code and return the output",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Python code to execute"}
            }
        }
    }
]

async def run_agent(task: str):
    messages = [{"role": "user", "content": task}]
    
    while True:
        response = await call_llm(messages=messages, tools=tools)
        
        if response.stop_reason == "end_turn":
            return response.content
        
        # Model wants to call a tool
        tool_use = response.tool_use
        tool_result = await execute_tool(tool_use.name, tool_use.input)
        
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": [{"type": "tool_result", "content": tool_result}]})
        
        # Loop continues until the model stops requesting tools
```

This is the ReAct pattern: the model reasons, takes an action, observes the result, and reasons again.

## Common failure modes

**Infinite loops.** An agent that calls a tool, gets an unexpected result, tries a different approach, encounters another problem, and loops indefinitely. Set a hard cap on iterations:

```python
MAX_ITERATIONS = 15

for iteration in range(MAX_ITERATIONS):
    response = await call_llm(...)
    if response.stop_reason == "end_turn":
        break
else:
    raise AgentTimeoutError(f"Agent exceeded {MAX_ITERATIONS} iterations")
```

**Error propagation.** When worker agents fail, the orchestrator needs to handle it gracefully. One failing worker should not silently invalidate the entire pipeline output.

**Prompt drift.** As conversation history grows over many tool calls, the model's behavior can shift. Important instructions in the system prompt receive less attention as the context fills with tool results. Periodically re-inject critical constraints.

**Compounding hallucination.** One agent generating inaccurate output that is passed as ground truth to the next agent amplifies the error. Add validation steps between agents for critical facts.

## When multi-agent adds value

Multi-agent architectures add complexity. They are appropriate when:

- Tasks are genuinely too long for a single context window
- Parallel execution of independent subtasks saves significant wall-clock time
- Different subtasks benefit from different prompting strategies or models
- A single agent would require too many tool calls to maintain a coherent reasoning chain

They are not appropriate when a single well-constructed prompt with one or two tool calls can accomplish the goal. More agents mean more latency, more cost, more places to fail, and harder debugging.

Start with the simplest architecture that could work. Add agents when you have a specific problem that a single agent cannot solve.

## Observability

Multi-agent pipelines are opaque by default. Add tracing from the start:

```python
import uuid

async def traced_call(agent_name, messages, tools=None, parent_trace_id=None):
    trace_id = str(uuid.uuid4())
    logger.info({
        "event": "agent_call_start",
        "trace_id": trace_id,
        "parent_trace_id": parent_trace_id,
        "agent": agent_name,
        "input_tokens": count_tokens(messages),
    })
    
    result = await call_llm(messages=messages, tools=tools)
    
    logger.info({
        "event": "agent_call_end",
        "trace_id": trace_id,
        "output_tokens": result.usage.output_tokens,
        "stop_reason": result.stop_reason,
    })
    
    return result, trace_id
```

With traces linked by parent ID, you can reconstruct the full execution tree of any agent run and diagnose which step failed.
