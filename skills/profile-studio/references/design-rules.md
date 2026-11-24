# Design rules

These rules come from real client rounds. Each one fixed a page that a client rejected.

## Photos

- Image first: every page opens with a full-width photo band that fades into the page colour.
- Pick photos by mood: calm, confident, at work. No stressed people, no staged thumbs-up, no clip art.
- One photo, one idea: the photo must match the page (a ledger for accounting, a handshake for advisory).
- Never use one photo on two pages that a reader sees close together.
- Keep faces out of the text area. Move the crop with `focus`, or pick a different photo.
- Do not put a stock face next to the name of a real person.
- Use only photos you have the right to print. Keep a `photos/CREDITS.md` with the source and licence of each one.
  Do not commit licensed stock photos to a public repository.

## Logo

- Use the logo in its true colours. Never invert it to white for a dark page.
- The logo sits on the light full-width band at the foot of the cover and the contact page.
  A small white box around a logo on a dark page looks pasted on.

## Colour

- Start from the brand colours in the logo. Set `accent` to the main brand colour and `secondary` to the second.
- A dark `ground` with one bright accent reads as premium. Light themes work too: set `ground` light,
  `heading` and `body` dark, and `band` to a light grey so it still reads as a band.
- Keep large areas calm. Do not fill a full page with the accent colour.

## Cover

- The `diagonal` style: hard-edged accent field cut at 45 degrees, photo in the lower triangle, thin bars.
  Set `face` to where the face is in the photo, so it lands in the open part of the triangle.
- The `photo` style: one full-bleed photo with the title at the lower left.
- Do not hand-draw curves, ribbons or swooshes. They look random. Straight cuts and photos look finished.

## Icons

- Use one icon set only (Lucide line icons are bundled). Put icons in outlined tiles, the same size on a page.
- Values: icon tiles with the word centred under each icon.

## Layout fixes

- `check` prints a WARNING when copy runs into a bar, a card or the footer. Fix the copy, not the type size.
- Look at full-size pages, not only the contact sheet: small overlaps are not visible at thumbnail size.
- A service page with little copy gets a taller photo band by itself. A page with too much copy needs a split.
- Client logo tiles are white by default. A logo that is white on colour needs `{"file": "x.png", "ground": "#34ce32"}`.
