# profile.json format

One file holds every word, colour and photo choice. The engine draws pages in the order of `pages`.

## Top level

| Field | Use |
|---|---|
| `version` | Draft label for the review copy, for example `"v3"`. |
| `company.name` | Short name. Used in the file name and as the logo fallback. |
| `company.legal_name` | Shown in the page footer and on the cover band. |
| `company.website` | Shown in the page header and on the bands. |
| `company.footer_label` | Right side of the footer. Default `Company Profile`. |
| `company.tagline_line` | Second line on the cover band. |
| `company.phone`, `company.email` | Used on the contact band if `band_lines` is not set. |
| `brand.logo` | Path of the logo file, relative to the profile folder. PNG with transparency is best. |
| `brand.colors` | Any of: `ground` (page), `surface` (cards), `border`, `accent`, `accent_light`, `accent_dark`, `secondary`, `heading`, `body`, `muted`, `ink` (text on the light band), `band` (the light band). |

## Fields for all page types

| Field | Use |
|---|---|
| `type` | One of the page types below. |
| `title` | Two lines, as a list: `["Our", "Services"]`. The second line is in the accent colour. |
| `contents_name` | The name in the contents list, if it differs from the title. |
| `photo` | File name in `photos/`. A missing photo draws a striped placeholder and a warning. |
| `focus` | `[x, y]` from 0 to 1: which part of the photo to keep when it is cropped. |

## Page types

| Type | Fields |
|---|---|
| `cover` | `style` (`diagonal` or `photo`), `kicker`, `title`, `subtitle`, `photo`, `face` (`[x, y]` of the face in the photo, diagonal style only). |
| `contents` | `heading` (default `CONTENTS`). The rows are made from the pages after it. |
| `about` | `lead`, `columns` (2 paragraphs), `stats` (up to 3 pairs: `["300+", "Clients"]`). |
| `leadership` | `lead`, `people` (up to 3: `name`, `role`, `bio`). |
| `values` | `mission`, `vision`, `values` (list of `name` and `icon`), `labels` (optional word changes). |
| `clients` | `hero` (`text`, `who`, `what`), `quotes` (up to 4), `logos` (files in `logos/`; a string or `{"file", "ground"}` for a coloured tile), `logos_label`. |
| `services` | `intro`. The list is made from the `service` pages: their title, `summary` and `icon`. |
| `why` | `intro`, `reasons` (up to 8: `icon`, `title`, `text`). |
| `service` | `summary`, `icon`, `intro`, `groups` (2 column headings, optional), `steps` (list, optional), `blocks`, `who`, `who_label`, `steps_label`. |
| `team` | `intro`, `groups` (up to 4: `name`, `members`). |
| `contact` | `headline`, `offices` (up to 3: `name`, `lines`), `people` (up to 2: `name`, `role`, `phone`, `email`), `band_lines`. |

## Service blocks

Each block is `{"name", "text", "bullets", "column"}`. `text` and `bullets` are both optional.
`column` is 0 (left) or 1 (right). Without `column`, the block goes to the shorter column.
The photo band at the top of a service page grows or shrinks to fill the free space.
The service number (01, 02 ...) comes from the order of the service pages.
