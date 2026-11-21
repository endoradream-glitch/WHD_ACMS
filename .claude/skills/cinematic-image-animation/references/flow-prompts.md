# Google Flow prompts for animation-ready stills

Flow/ImageFX/Whisk are free but manual and login-gated. Produce all prompts together so the style stays locked.

## Template (copy per shot)
`[STYLE LOCK], [SUBJECT + action], [SHOT: wide|medium|close-up], [LIGHT], [COMPOSITION], 9:16 vertical`

- **STYLE LOCK** (identical in every prompt): e.g. `cinematic 3D animated film still, soft painterly textures, shallow depth of field, rich color grade`
- **Character lock:** describe the character the same words every time (hair, outfit, colors); use Whisk's subject/style reference image for consistency.
- **Light words** match the storyboard shift: `golden hour backlight`, `cool moonlight rim light`, `neon glow`, `god rays through window`.
- **Composition for motion:** leave empty space on the side you will pan toward; keep the subject near a third line; put foreground elements (leaves, window frame) in front so tiltshift/pull_in has something to blur.
- Ask for **extra margin**: `subject centered with generous negative space around` so 1.2-1.4x zoom stays clean.

## Example set (6 shots)
1. `...wide establishing shot of a lantern-lit village at dusk, space on the right`
2. `...medium shot of the hero walking, foreground branches blurred`
3. `...close-up of the hero's face, warm rim light`
4. `...over-the-shoulder looking at a glowing doorway`
5. `...wide, doorway opens with bright god rays`
6. `...close-up, hero smiling in soft light`
