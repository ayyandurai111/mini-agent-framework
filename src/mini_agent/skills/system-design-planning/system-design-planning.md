---
name: system-design-planning
description: Use when user wants to design/architect/plan a software system before building — "design X", "architect this", "plan the backend", "how would you build this". Trigger even from a product idea + "how would you build this".
---

# System Design Planning

Steps (skip full flow for narrow scoped questions like "Redis vs Memcached" — just answer directly):

1. **Requirements**: functional (3-6 features), non-functional (scale/latency/availability), constraints. Ask max 2-3 questions if unclear, else assume sensibly and state it.
2. **Scale**: rough users, read/write ratio, data size, traffic pattern. Don't over-engineer if not needed.
3. **High-level design**: component diagram (ASCII/mermaid), data flow for top use case(s), monolith vs microservices + why.
4. **Deep dive**: only 1-3 riskiest components — schema, API contract, scaling/failure behavior.
5. **Trade-offs**: 2-4 key decisions, alternative considered, why rejected.
6. **Summary**: 2-3 line architecture summary, stack, build order, open risks.

Output: skimmable, bullets, diagram if 3+ components. Save as file only if asked.
