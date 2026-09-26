# Validation Results — 2026-09-26

Branch: `arena/01a0dc7f-arena`, assigned by Arena (the requested `arena/probe-artifacts` could not be used). Base commit: `main` @ `1263076`.

Tools used: Python 3 with `pypdf`, `openpyxl`, `Pillow` and `reportlab`. None of these were preinstalled; all were installed with `pip install --break-system-packages`.

## Per-format status

| File | FILE_CREATED | FILE_VALIDATED | Validation method & result | GITHUB_COMMITTED | USER_ACCESSIBLE |
|---|---|---|---|---|---|
| research.md | yes | yes (structural) | 10,341 bytes; 9 `##` sections | see PR | via PR/branch on GitHub |
| sources.json | yes | yes | `json.load` OK; 9 sources (6 first-party incl. runtime R1); every source has all required fields | see PR | via PR |
| sample.csv | yes | yes | `csv.DictReader` read back 6 rows × 5 columns | see PR | via PR |
| sample.pdf | yes | structural only | `%PDF-1.4` header and `%%EOF` trailer; `pypdf` opens it (1 page, title metadata); text extraction contains "C6". **Not rendered in a PDF viewer.** | see PR | via PR (GitHub shows PDFs in its viewer) |
| sample.xlsx | yes | structural only | ZIP `testzip()` clean; `openpyxl` reloads it (7 rows; formula `=COUNTA(A2:A100)` stored). **Formula not calculated. Not opened in Excel or LibreOffice (neither installed).** | see PR | via PR (download only) |
| sample.png | yes | yes | `PIL.Image.verify()` OK; PNG, 480×160 | see PR | via PR (GitHub shows images) |

Not attempted: `sample.docx`, `sample.pptx` and `sample.html`. These libraries are not preinstalled, and without an office suite the files could only be checked structurally, the same limit as for XLSX. `sample.html` was skipped because Markdown already covers that need.

## Repository hygiene

- Secret scan (regex for `ghp_`, `github_pat_`, `sk-`, `AKIA`, `password=` and private-key headers): no matches.
- `git status` before commit: the only untracked path is `docs/probes/` (the new directory). No existing files were modified.
- No temporary files: the generator script ran from stdin, and no `__pycache__` folder was created.

## Commit / PR

The commit SHA and PR URL are reported in the final chat response. A file cannot record the SHA of the commit that contains it.

GitHub accessibility can only be confirmed after the push (checked with `gh pr view` / `gh api`).
