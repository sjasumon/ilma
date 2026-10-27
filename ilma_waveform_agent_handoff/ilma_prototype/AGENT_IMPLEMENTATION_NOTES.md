# ILMA — Living waveform home screen (agent handoff)

## Files
- `ilma-waveform.html`: One-file, framework-free visual and interaction prototype. Open directly in a browser.

## Product intent (important)
This first screen is *intentionally nearly empty*. It is **voice-first for blind and low-vision users**, not a conventional banking dashboard. **Do not add cards, suggestions, headlines, or onboarding clutter** to the first screen without an explicit product decision. Preserve the large touch target, accessible labels, screen reader status announcements, keyboard focus, high contrast and reduced motion support.

## Visual reference
- Dark emerald gradient background.
- Top logo in Bangla plus ILMA, language and settings controls.
- Center **horizontal living waveform**, not an orb, gold + cyan curves with restrained particles.
- Bengali guidance below, and four-item bottom navigation.
- Smooth but gentle voice-state-responsive animation.

## Interaction contract
- Main speech surface covers the space between header and bottom navigation and is one button (`role=button`, `tabindex=0`).
- Tap anywhere **within the voice surface** (not settings, language, or navigation) to start/stop listening.
- Keyboard Enter and Space trigger it.
- No automatic microphone capture on page load. Request mic permission only on activation, and handle denied permission with spoken or announced guidance.
- Screen-reader status text must accurately reflect listening/processing/speaking state.
- Reduce-motion preference disables decorative motion.
- `window.ILMAPrototype.setVoiceState('idle'|'listening'|'thinking'|'speaking')` is the stub API in the HTML; replace with real voice pipeline state events.
- Do not fake "listening" as actual capture in production. **The HTML is a design demo only**; it toggles visual state without capturing microphone audio or running AI.
- No fake functioning banking tabs. Connect to real navigation and keep proper accessible titles/roles.

## Development integration
1. Replicate the provided layout in the target framework with responsive sizing and safe-area insets.
2. Implement actual microphone capture with permission, input levels, voice activity detection, error / interruption handling, speech-to-text or real-time audio transport, AI response, TTS, and cancel/stop operations.
3. Use actual amplitude data to drive waveform within constrained motion; idle can be slow decorative animation.
4. Preserve accessible state announcements, native button semantics if possible, localization and tab order.
5. Test with TalkBack (Android), VoiceOver (iOS), desktop keyboard, 200% text zoom, reduced motion, and narrow phone screens. Screen readers must announce that voice capture is ready, in progress, has stopped, or has failed.
6. For users who cannot speak, add an accessible text-input route (perhaps settings or a secondary voice-surface action), **without cluttering the main screen**.
7. Avoid always-on microphone and permission prompt before user action.

## Caveats
Fonts render best with locally available Bangla fonts; use the project's installed licensed font assets if a pixel-perfect match is needed. Bengali text should not be replaced by an image. The waveform is native SVG/CSS and remains crisp at all sizes.
