# Local

## Technical Content Pipeline

A full-cycle pipeline that turns high-signal technical video (AI engineering,
DeFi/blockchain infrastructure, business operating systems) into clip specs
and long-form X Articles.

| Path | Purpose |
|---|---|
| `.claude/skills/technical-content-pipeline/SKILL.md` | Operating instructions Claude follows (Mode A sourcing, Mode B package production, style rules) |
| `pipeline/templates/mode-a-input.md` | Input form for sourcing and ideation |
| `pipeline/templates/mode-b-input.md` | Input form for transcript processing |
| `pipeline/templates/output-package.md` | Skeleton of the four-part publish package |
| `pipeline/lint_package.py` | Checks a finished package against the structural and editorial rules |
| `pipeline/drafts/` | Where generated packages are saved |

### Usage

1. In Claude Code, run `/technical-content-pipeline` or just paste a filled
   input template.
   - **Mode A:** give a niche or topic. You get 3 source candidates, a target
     thesis, and a tier recommendation.
   - **Mode B:** give a transcript. You get cut specs, a hook, the article, and
     an engagement plan.
2. Lint the draft:

   ```sh
   python3 pipeline/lint_package.py pipeline/drafts/<draft>.md --tier 2 --transcript transcript.txt
   ```

   The linter checks tier duration windows, headline length (4–8 words), hook
   length (2–4 lines plus attribution), deconstruction item count (3–5), the
   navigational index (4–8 stamps, required for Tier 2 and 3), keyword count
   (3–5), banned hype phrases, the `<!-- value-add -->` marker, and whether
   the timestamps appear in the transcript.
