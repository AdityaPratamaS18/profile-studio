# Contributing

Thank you for helping. Small, tested changes are the easiest to accept.

## Rules

1. Keep the words in `profile.json`. Do not hard-code text in the page functions.
2. Add only files that are free to redistribute: no stock photos, no paid fonts, no real company logos.
3. Do not commit real client profiles, photos or contact details.
4. Run the test before a pull request: `bash tests/smoke_test.sh`.
5. For a layout change, look at the changed pages at full size (`pdftoppm -png -r 80`), and add a screenshot to the pull request.
6. Do not use em-dashes or en-dashes in docs or code. CI checks this.
7. Update `CHANGELOG.md` and, for a release, the `version` in `.claude-plugin/plugin.json`.

## New page types

Add a function `p_<type>(c, cfg, d)` in `profile.py`, add it to `PAGE_TYPES`, document its fields in
`references/profile-format.md`, and use it in the example profile so the smoke test covers it.
