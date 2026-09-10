# Idea: Claude-powered self-assessment (a shareable "where should I practice?" tool)

**Status:** idea only — nothing built. Written to hand to Rick for reaction.
**Scope:** PBS-side artifact + (later, maybe) a Bridge Classroom on-ramp.
**BC engine impact:** none required for the first version. This does **not** ask
Rick to change the BC engine.

---

## The capability, in one paragraph

A published Claude "artifact" is a self-contained web page hosted on claude.ai.
It can now be granted a runtime ability to **call Claude from inside the page** —
so instead of a static quiz that shows everyone the same result, the page collects
a player's answers, sends them to Claude live, and renders a **personalized**
response. No API key, no server, no separate quiz platform: you describe the page,
Claude builds it, and you share one link that works for anyone who opens it.

## What I'd build with it

A short **bridge self-assessment**. A player answers 8–10 plain questions about
what they know and play — "Do you play 2/1 game forcing? How comfortable are you
with reverses? Have you tried Smolen? Weak twos — feature or Ogust?" — and Claude
writes back a **personalized study plan that points at our existing PBS scenarios**,
in a sensible order:

> "Start with Weak_2_Bids, then Inverted_Minors, then Reverses. Once those feel
> automatic, add New_Minor_Forcing and Fourth_Suit_Forcing."

The value is **personalization + routing into the library we already have**. The
player gets a plan tailored to their gaps; we get a friendly front door that sends
people to the right practice deck instead of leaving them to browse ~400 scenarios
cold. It's one link — shareable in the Facebook group, the Discord, or from within
Bridge Classroom.

## Why this fits us specifically

- **It routes to verified content instead of inventing bridge.** Every scenario it
  recommends is one we've already built and engine-checked. Claude is choosing an
  *ordering*, not adjudicating a bid.
- **Zero infrastructure.** No new platform, no monthly tool fee, no dev cycle.
- **Low commitment.** A private link first; nothing is public until we decide it's
  good enough to share.

## The honest caveat (this is the important part)

Claude *inside an artifact has no access to our verification stack* — no BBA/GIB
answer key, no `.bbsa`, none of the corpus of known engine misbids we work around.
So the moment a page asks Claude to **judge a specific bid as right or wrong**, it
can sound confident and be wrong, with nothing to catch it.

That's why the first version is a **router, not a judge**: it recommends decks,
it doesn't grade bidding. If we ever want an interactive "what would you open?"
coach, we'd tame it by pinning it to hands we've *already* verified — Claude
explains the known answer rather than deriving one from scratch.

## Variations (in rough order of risk)

1. **Study-plan router** *(recommended first)* — ranks and links existing PBS
   scenarios into a personalized sequence. Claude routes, never adjudicates.
2. **Skill scorecard** — scores the player across areas (opening, responses,
   conventions, competitive) with a level read, then routes. A bit more judgment
   from Claude.
3. **"What would you open?" coach** — interactive, and the risky one; only viable
   over a pre-verified hand set.

## What a first version would take

- Pull the real scenario list from `btn/` / `-PBS.txt` so recommendations point at
  actual files.
- Write the question set and the routing logic (which gaps → which decks, in what
  order).
- Build the page, share a **private** link, poke at it, decide whether it's worth
  showing anyone.

Roughly an afternoon to a first clickable draft.

## Open questions for Rick

- Is a Claude-powered on-ramp something you'd want to eventually live **inside**
  Bridge Classroom, or is a standalone shared link the right home?
- Does the "router, not judge" boundary match how you'd want Claude used in
  anything player-facing?
- Any assessment areas you'd want it to cover (or deliberately avoid) for the
  audience you have in mind?
