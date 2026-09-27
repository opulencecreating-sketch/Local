# Mode A Brief: Multi-Agent Memory Drift

- **Niche:** AI Engineering
- **Prepared:** 2026-09-27
- **Verification:** titles, dates, runtimes and URLs were checked against YouTube and Latent Space on the prep date. Chapter timestamps come from YouTube, Latent Space, and ai.engineer's talk pages (ai.engineer's are editorial summaries). **Confirm every timestamp against the raw transcript before Mode B.**

---

## 1. Source Candidates

### A. Anthropic Workshop: Build Agents That Run for Hours (primary)
- **Channel:** AI Engineer (@aiDotEngineer)
- **Speakers:** Ash Prabaker & Andrew Wilson, Anthropic (X handles unverified: `@[handle?]`)
- **Published:** 2026-05-18 · **Runtime:** 1:15:40
- **URL:** https://www.youtube.com/watch?v=mR-WAvEPRwE
- **Why it's high-signal:** The team that builds the harness says compaction doesn't fix drift ("Compaction produces lossy summaries, and those summaries can drift" ~36:39). They show what does: a planner/generator/evaluator split with a shared filesystem, the original spec re-inserted into every session (~45:45), and structured handoffs to the critic instead of raw traces (~56:21). Every claim comes with a concrete mechanism you can implement.
- **Key chapters (ai.engineer):** 7:55 context policy and exit · 23:42 negotiate "done" before code · 34:14 remove scaffolding · 36:39 evaluation boundary · 45:45 restart without losing the product boundary · 52:01 per-role evals and usable history · 56:21 the critic needs distance · 1:13:25 read the trace from the model's POV

### B. Total Recall: Agent Memory and Harness Engineering
- **Channel:** AI Engineer (@aiDotEngineer)
- **Speaker:** Ignacio Martinez, Oracle (X handle unverified: `@[handle?]`)
- **Published:** 2026-09-18 · **Runtime:** 1:00:47
- **URL:** https://www.youtube.com/watch?v=xs-ob87TTzg
- **Why it's high-signal:** Martinez frames drift as a storage-semantics problem. File-based memory has no transactional consistency, so 8–32 parallel agents writing to it corrupt shared state (~16:39). Git worktrees only "move the collision to a later merge" (~18:35). This is the database angle most agent talks skip.
- **Key chapters:** 13:48 where memory lives changes how agents collaborate · 21:34 retrieval creates more data than the source · 25:53 remember selectively, then assemble · 34:04 refresh context every iteration

### C. The Age of Async Agents: Cognition's Walden Yan & OpenInspect's Cole Murray
- **Show:** Latent Space (hosts incl. swyx; handles unverified: `@[handle?]`)
- **Guests:** Walden Yan (@walden_yan), Cole Murray (`@[handle?]`)
- **Published:** 2026-05-28 · **Runtime:** ~1:08
- **URL:** https://www.latent.space/p/cognition · video: https://www.youtube.com/watch?v=0fgJPhYcbVk
- **Why it's high-signal:** Yan wrote *Don't Build Multi-Agents* (June 2025), the essay the "shared context" debate started from. Here, a year of production data later, he reports that parallel agents still mostly follow the manager/sub-agent pattern (~37:46) and hints the essay will get a revision (~39:08). He also walks through Devin's memory evolution from "Knowledge" to memory.md-style files (~29:50), and describes codebases decaying after about two weeks of unsupervised agent work (~44:18). That last one is drift showing up in the artifact, not the context.
- **Key chapters (Latent Space):** 28:59 Memory, Knowledge, and Always-On Agents · 36:16 Sub-Agents, Multi-Agent Orchestration, and Meta-Devin · 43:55 Vibe Coding, Auto-Merge, and Codebase Decay

**Considered and set aside:** Latent Space × Lance Martin, *Context Engineering for Agents* (2025-09-11, https://www.youtube.com/watch?v=_IlTcWciEC4). It's good background on context isolation, but it's a year old and the 2026 sources above supersede it.

---

## 2. Target Angle

> **Multi-agent memory drift is a concurrency-control problem, not a context-window problem. Bigger windows and better compaction make it worse, because every summary is a lossy, unversioned replica of shared state.**

How the three sources support it:
- **Anthropic (A):** compaction summaries drift. The fix is an authoritative spec re-injected every session, plus structured, schema'd handoffs. That's a *source of truth + replication protocol*.
- **Oracle (B):** file memory lacks ACID guarantees, and worktrees defer conflicts instead of resolving them. That's a *write-coordination* failure.
- **Cognition (C):** manager/sub-agent topologies persist because a single writer is the only coordination model that has held up in production. That's *single-leader replication*.

**Value-add the article can bring (not said in any clip):** map agent memory onto distributed-systems vocabulary:
- compaction = lossy log truncation
- spec re-injection = reads from the leader
- structured handoff = a typed message contract
- worktrees = optimistic concurrency with merge-time conflict resolution

Then offer a falsifiable test readers can run: *if two sub-agents can hold contradictory beliefs about the same fact and nothing detects it, you have a replication bug, not a prompting bug.*

**The counterargument to address:** Martinez's own framing implies a database fixes it. But ACID handles *write* conflicts, not *semantic* ones: two agents can both commit valid rows that contradict each other. That gap is the open question for the reply thread.

---

## 3. Tier Recommendation: **Tier 2 (15–30 min), cut from Source A**

- **Density:** the argument needs three beats back to back. (1) Compaction drifts. (2) Shared filesystem plus spec re-injection. (3) Why the critic gets a structured handoff, not the builder's reasoning. A 3–8 minute cut can land one beat but not the causal chain.
- **Stands alone:** Chapters ~34:14 → ~56:21 run from "remove scaffolding when behavior improves" through "the critic needs distance". That span is self-contained and needs no setup from the first half hour. **Provisional cut: ~[35:56] → ~[56:21] (about 20m25s).** Confirm the exact boundaries in the transcript.
- **Why not Tier 3:** the full 75-minute workshop spends its first 30 minutes on model history and demos, which dilute the drift thesis.
- **Tier 1 companion (optional thread follow-up):** Source B, ~[13:48] → ~[21:34] (about 7m46s). It's one mechanism: files vs. transactional memory under parallel agents. It works as a standalone micro-clip that backs up the concurrency framing.

---

## Next step (Mode B)

Pull the raw transcript for `mR-WAvEPRwE` (the `watch` skill or the vidIQ transcript tool can fetch it). Fill `pipeline/templates/mode-b-input.md` with Tier 2 and run the package. Add `@handles` for Prabaker, Wilson, and Martinez once confirmed.
