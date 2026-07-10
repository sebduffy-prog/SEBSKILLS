# Attribution

`scripts/memory_stream.py` ports the memory-stream retrieval scoring from
joonspk-research/generative_agents (Apache License 2.0), specifically
reverie/backend_server/persona/cognitive_modules/retrieve.py. The scoring math
(per-component min-max normalisation + weighted sum), the [0.5, 3, 2] weights,
and the 0.995 recency decay follow that source and Park et al., "Generative
Agents: Interactive Simulacra of Human Behavior" (UIST '23).

Original license: Apache-2.0 — https://github.com/joonspk-research/generative_agents/blob/main/LICENSE
