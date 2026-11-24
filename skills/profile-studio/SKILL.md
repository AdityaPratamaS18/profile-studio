---
name: profile-studio
description: Make a print-ready company profile (A4 PDF brochure) for a business, with live text, icons, photos and the true-colour logo, plus a Word review copy of the words for the client to approve. Plans the content first, then builds every page from one profile.json and checks the result. Use when the user wants a company profile, corporate brochure, capability statement, firm profile, agency credentials deck in print, "a profile like <another firm's>", or wants to update, restyle or rebuild a profile made with profile-studio.
argument-hint: "[new <folder> | build <folder> | check <folder> | docx <folder>]"
---

# profile-studio

You make a finished company profile with the user. One profile is one folder with one `profile.json`,
a `photos/` folder, a `logos/` folder for client logos, and the company logo file.
The tool is `python3 "${CLAUDE_SKILL_DIR}/scripts/profile.py"` (call it PROFILE below).

| Command | What it does |
|---|---|
| `PROFILE doctor` | Checks Python packages and the optional poppler tools. |
| `PROFILE new <folder> --name "Firm"` | Copies the example profile into a new folder. |
| `PROFILE build <folder> [--pages 3,9-11]` | Builds the PDF into `<folder>/build/`. |
| `PROFILE check <folder>` | Builds, then checks fonts, words, layout warnings and makes a contact sheet. |
| `PROFILE docx <folder>` | Writes the Word review copy of the words. |

## The process

Work in this order. Each stage ends with the user's approval. Do not skip to design.

1. **Setup.** Run `PROFILE doctor`. If a package is missing, install it with the command it prints.
2. **Collect the facts.** Ask for the old profile, the website, and any brief. Read them all.
   When two sources disagree, ask the user which one is final. Do not invent facts, numbers, clients or quotes.
3. **Plan the content.** Run `PROFILE new <folder>`. Replace the example words in `profile.json` with the
   real content. Read `references/content-rules.md` first.
4. **Review copy.** Run `PROFILE docx <folder>` and give the user the .docx for client sign-off.
   Change the words in `profile.json` only, then make the .docx again. Raise `version` for each new round.
5. **Photos and logo.** Ask the user for the logo file and for photos they have the right to use.
   Read `references/design-rules.md` for how to pick photos. Put them in `photos/` and set `photo` on each page.
6. **Build and check.** Run `PROFILE check <folder>`. Look at the contact sheet AND at full-size pages
   (`pdftoppm -png -r 80 -f N -l N`). Fix every WARNING. A clean check is required, not a nice extra.
7. **Show and iterate.** Send the PDF. Change one thing at a time. Rebuild only the pages that changed
   with `--pages` while you work, then do a full `check` before each delivery.

## Rules that always apply

- The words live only in `profile.json`. Never edit words inside the PDF or hard-code them in the script.
- Never invert, recolour or crop the logo. It sits in its true colours on the light footer band.
- Do not put text over a face in a photo. Use `focus` (and `face` on the cover) to move the crop.
- Do not use stock photos of people next to the names of real staff. Use a team or office photo instead.
- Use only photos and logos the user has the right to print. Record the source of each stock photo.
- Keep client documents free of internal notes: no "draft by", no layout notes, no "to confirm" flags,
  unless the user asks for them.
- If the copy for a page does not fit, shorten the copy or split the page. Do not shrink the type.

## Files to read

- `references/profile-format.md`: every page type and every field in `profile.json`. Read it before you edit.
- `references/content-rules.md`: how to plan and write the content. Read it at stage 3.
- `references/design-rules.md`: photos, colour, icons, layout fixes. Read it at stages 5 to 7.
- `templates/example/profile.json`: a full 14-page example for a fictional firm.

## Icons

Icons are Lucide line icons (ISC licence) in `assets/icons/`. Use the file name without `.svg`
(for example `calculator`, `shield-check`). To add an icon, copy its SVG from the `lucide-static`
npm package or lucide.dev into `assets/icons/`. An unknown name prints a warning and draws a check mark.
