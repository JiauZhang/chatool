---
alwaysApply: true
name: "self-evolver-rule"
description: "Evolves the skill/rule ecosystem by detecting user dissatisfaction signals. Invoke when user clearly dislikes your output approach, style, or decisions."
---

# Self Evolver

A meta-rule that keeps the skill/rule ecosystem healthy by learning from user dissatisfaction.

## Essence

The core signal is simple: **the user is unhappy with what you just produced or how it approached a task**. This manifests in many forms — explicit rejection, correction, restating requirements differently, or even just a tone of frustration. The exact wording doesn't matter; what matters is recognizing that the output missed the mark.

When that happens, this rule decides whether the ecosystem needs to grow (new skill/rule) or adapt (existing skill/rule improvement).

## What to Watch For

Any clear indication that the AI's output didn't meet expectations:

- Correcting the approach: "不要...", "应该用...", "不对", "not like this"
- Restating preferences: "我说过...", "跟你说过了...", "as I mentioned..."
- Quality feedback: "太复杂了", "这不是我要的", "too verbose", "wrong approach"
- Tone shifts that suggest dissatisfaction

The form doesn't matter. The signal does.

## Evolution Logic

When dissatisfaction is detected:

1. **Understand the complaint** — What exactly was wrong? The approach? Style? Technology choice? Quality?

2. **Check existing skills/rules** — Look through your skills/rules to see if anything already addresses this concern.

3. **Decide**:
   - If an existing skill/rule already covers this, it's probably not being followed well — **optimize** it to make the instructions clearer or triggers more reliable.
   - If no skill/rule covers this and the feedback represents a clear, repeatable preference, **create a new skill/rule**.
   - If it feels like a one-off complaint or unclear signal, **do nothing** — just keep it in mind for the session.

4. **Act** — Create or update the skill/rule file. New skill/rule should capture what the user wants (not just what they don't want). Optimizations should sharpen existing instructions without losing their original intent.

## Guiding Principles

- Never create a skill/rule from a single ambiguous complaint. Wait for clarity or repetition.
- A skill/rule's job is to prevent the same mistake from happening again. If it won't serve that purpose, don't create it.
- Positive framing is more useful: capture what TO do, not just what NOT to do.
- When optimizing, preserve the original intent while incorporating the new signal.