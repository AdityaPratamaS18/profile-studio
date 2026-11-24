# Security

## Report a problem

Report security problems in private: https://github.com/AdityaPratamaS18/profile-studio/security/advisories/new

Do not open a public issue for a security problem. The maintainer aims to answer within 7 days.

## What the tool does

| Item | Behaviour |
|---|---|
| Network | None. The tool reads and writes local files only. |
| Keys | None needed. |
| Telemetry | None. The tool sends nothing to the author. |
| Files written | Only inside the profile folder you give it (`build/`), and the new folder for `new`. |

## Client data

A profile holds a client's names, phone numbers and photos. Keep real profiles out of public repositories.
The `.gitignore` of this repo excludes `build/` and `profiles/`.

## Supply chain

- The tool uses reportlab, Pillow, svglib and python-docx, plus the poppler tools for checks.
- The GitHub Actions in this repo are pinned to commit SHAs and run with read-only permissions.
