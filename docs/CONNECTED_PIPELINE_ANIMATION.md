# Connected pipeline animation

This is the agreed presentation contract for the ATS Final Boss process timeline, clarified on 3 October 2026.

## Visible content and guide paths

Step numbers, titles, descriptions and dots remain visible throughout horizontal scrolling. Do not gate text opacity on viewport entry or line arrival. The faint horizontal track and faint vertical branch tracks are visible before progress reaches them. The orange horizontal fill and vertical strokes are separate animated layers.

## Connected motion

The rendered horizontal pan determines the horizontal fill tip and the last reached milestone. When that tip reaches a dot, the colored vertical stroke grows from the dot toward its text over 350 ms. Top branches grow upward using a bottom transform origin; bottom branches grow downward using a top origin. Reversing past a dot retracts its stroke, preserving the text, dot and faint track. The 0.5 px arrival tolerance accommodates subpixel rounding. Branch animations overwrite prior branch tweens when direction changes.

The line endpoint is derived from first/last milestone geometry. Navigation uses measured step positions, not evenly spaced overall scroll percentages, because the introductory cover and responsive widths change the distance. Trailing space keeps the final milestone reachable. Free scrolling uses the pan's scrubbed position; navigation settles its pan immediately. Vertical strokes have a short timed growth after arrival, rather than pretending they share horizontal distance.

## Implementation map

- `src/app/assets/pipeline-timeline.js`: rendered pan, measured targets, progress, branch state, navigation and route lifecycle.
- `src/app/assets/style.css`: `.pipeline-milestones` pseudo-elements form the horizontal track/fill; `.pipeline-step:before` is the permanent vertical path; `.pipeline-stem` is the colored stroke.
- `src/app/index.html`: milestone text and semantic navigation.

No text reveal tween is needed. On teardown, cancel branch tweens, revert the GSAP context, clear generated styles and restore the static layout. Small/short viewports and reduced-motion settings use a vertical static sequence without decorative line animations.

## Verification

Check intermediate scroll positions as well as buttons. With step 1 active, upcoming visible steps must retain opacity 1 and show faint branch tracks, while colored unreached strokes remain collapsed. At step 2, the first two strokes finish growing; later strokes stay collapsed, and all text stays opaque. Check reversal, resize, final-step access, route cleanup, themes and static fallback. JavaScript syntax and preview export checks supplement browser verification; backend regression counts do not establish motion correctness.

A local Codex skill named `connected-pipeline-timeline` preserves this contract and a reference implementation snapshot. The skill is a development aid; it is not a website runtime dependency.
