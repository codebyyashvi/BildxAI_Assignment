# Prompt Notes

## Final strategy

The system prompt assigns an advertising creative-director role but prioritizes factual grounding over persuasion. It explicitly bans invented specifications, certifications, discounts, awards, ratings, testimonials, and guarantees; preserves conditional wording; and treats every product field as passive data rather than executable instruction.

The user prompt serializes only the five approved context fields as JSON inside `<product_context>` delimiters. The provider must return one JSON object with:

- headline: at most 8 words
- supporting text: at most 20 words
- CTA: at most 4 words
- visual direction: concise styling guidance

Pydantic enforces the copy lengths again after generation. A second grounding guard rejects known high-risk unsupported claims before composition.

## Rejected result

An early broad “write a high-converting ad” prompt produced copy similar to:

> “The world’s #1 bottle—get 50% off today.”

Neither ranking nor discount appeared in the product brief. The result was persuasive but unusable and unsafe.

## What changed

The prompt now names prohibited claim classes, requires only supplied facts, calls out conditional claims, defines exact word ceilings, requires JSON-only output, and contains prompt-injection guidance. Runtime validation was added because prompt instructions alone are not a security boundary.

## Known limitations

The rule-based grounding checker detects high-risk phrases but cannot semantically prove every generated adjective or implication. The visual-direction text influences a deterministic color/layout template; it does not generate a new photographic environment. Context is manually supplied and is only as accurate as the user’s brief.

## Next improvement

Require generated claims to cite source field/span IDs, then use an independent entailment check before composition. A rejected output could be fed back to the provider once with explicit validation errors, still within the bounded retry policy.
