---
title: "Fine-tuning vs prompting: when each one is the right tool."
description: "What fine-tuning actually does, when it outperforms prompting, and when prompting is the better choice."
pubDate: 2025-09-08
tags: ["DevOps"]
draft: false
---

Fine-tuning and prompting are both ways to control LLM behavior. They work differently, cost differently, and are appropriate for different problems. Choosing between them without understanding the distinction leads to spending months fine-tuning when a better prompt would have worked, or writing elaborate prompts when fine-tuning would produce better results with less ongoing effort.

## What prompting does

Prompting shapes model behavior at inference time. You write instructions, provide examples, and structure the context to elicit the output you want. The model's weights are unchanged. Different prompts produce different outputs from the same model.

```python
# Zero-shot: just describe the task
prompt = "Classify the sentiment of this review as positive, negative, or neutral."

# Few-shot: provide examples
prompt = """Classify sentiment. Examples:
"Amazing product!" -> positive
"Stopped working after a week" -> negative
"It arrived on time" -> neutral

Now classify: "The instructions were confusing but it works fine"
"""
```

Few-shot prompting is the closest thing to "light fine-tuning" available without touching the model. Adding 3-10 examples to a prompt often produces near-fine-tuned quality for straightforward tasks.

## What fine-tuning does

Fine-tuning updates the model's weights using training examples. The model learns patterns from your data and incorporates them into its parameters. After fine-tuning, the model produces the trained behavior without needing examples in every prompt.

This matters in two scenarios:

**Consistent format or style requirements.** If every response must follow a rigid JSON schema, always use specific terminology, or match a particular voice, you can enforce this with long few-shot prompts. But fine-tuning internalizes the pattern so you do not need to include examples in every call. This reduces prompt length and improves reliability.

**Domain-specific knowledge or behavior that prompts cannot teach.** If the model consistently makes errors on your specific domain - misidentifies technical terms, uses incorrect field values, confuses similar concepts unique to your business - prompting can partially correct this but fine-tuning can address it at the weight level.

## When to choose prompting

Prompting is the right starting point for almost every problem. It is fast to iterate, costs nothing to change, and you can evaluate output quality immediately.

Choose prompting when:
- You are still figuring out what good output looks like
- Your requirements change frequently
- You need interpretability (you can read the prompt and understand why the model does what it does)
- You have fewer than a few hundred high-quality labeled examples
- The task involves general reasoning or knowledge that the model already has

Never fine-tune before exhausting the prompt design space. Chain-of-thought prompting, structured output format constraints, example-rich system prompts - many problems that seem to require fine-tuning are actually prompting problems.

## When to choose fine-tuning

Fine-tuning becomes worth its cost when:

**You have a large volume of inference calls.** A fine-tuned smaller model may outperform a prompted larger model at a fraction of the cost. If you make millions of calls per day, the cost difference is significant.

**You need reliable format adherence at scale.** Few-shot examples in every prompt add tokens and do not guarantee perfect adherence. A fine-tuned model can reliably output a specific JSON structure with field names and value ranges from your domain.

**You have high-quality labeled data.** Fine-tuning requires examples of inputs paired with ideal outputs. If you have 1,000+ labeled examples that represent the task distribution, fine-tuning is feasible. With 50 examples, expect poor results.

**You are trying to change the model's default behavior, not just guide it.** Teaching the model that in your domain, "churn" means customer cancellation (not ice cream), that your product names follow a specific pattern, or that your output format always includes a specific field - these are model behavior changes that fine-tuning handles better than prompting.

## The false belief

Fine-tuning does not make a model smarter. It makes a model consistent about your specific patterns. If the base model cannot do the task reliably with good prompting, fine-tuning on typical examples will not fix fundamental capability gaps.

Fine-tuning is also not a way to add knowledge. Training on text does not reliably inject facts into model weights in a retrievable way. For knowledge that changes or needs to be cited, use RAG.

The right sequence: prompt first, establish what good looks like, collect real examples from successful prompts, then consider fine-tuning if you have sufficient data and a cost or consistency reason to do so.
