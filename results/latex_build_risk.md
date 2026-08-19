# LaTeX build risk: priced

Date: 2026-08-19. arXiv target 2026-09-15 (27 days out).
Scope: verify the "no toolchain, never compiled" finding, and establish whether
`paper/main.tex` is well-formed without a compiler.

---

## 1. The number the schedule can use

**Estimated cost to first compiled PDF: 15-60 minutes of wall-clock, one-time, no
research work.** Not days.

That splits into:

| Component | Cost |
| --- | --- |
| Install a toolchain (cheapest route, WSL apt) | **49.1 MB download, 21 packages, 144 MB on disk, ~5 min** |
| Fix source errors found by static validation | **0 known** (see section 3) |
| Residual: errors only a real compiler can surface | 0-45 min, see section 5 |

The schedule agent's finding is **confirmed on the toolchain and over-priced on the
consequence**. There is genuinely no LaTeX anywhere on this machine and no PDF has
ever been produced. But the implied cost -- "a paper that has never been compiled can
be arbitrarily far from building" -- does not hold here: the source passes every
structural check that can be run without a compiler, with zero blocking errors. This
is the smallest of the three cost components, not the largest, and the install is
~50 MB, not the multi-gigabyte job the "do not start an unattended install"
constraint was written to guard against.

**Recommended action: install `texlive-latex-base texlive-latex-recommended
texlive-fonts-recommended` inside WSL Ubuntu-24.04 (49.1 MB) and build from
`paper/`.** I did not install it -- that is the user's call. See section 6.

Risk reduction delivered here: `scripts/check_latex_source.py`, a dependency-free
re-runnable validator that reproduces section 3 in one command and exits non-zero on
any blocking error. See section 7.

---

## 2. Toolchain verification: the finding is correct, and it is correct in WSL too

The schedule agent checked Windows only. I checked both. Nothing is installed on
either side.

**Windows** (`Get-Command`, 12 binaries): `pdflatex`, `latexmk`, `xelatex`,
`lualatex`, `tectonic`, `miktex`, `miktex-console`, `tex`, `bibtex`, `biber`,
`pdftex`, `kpsewhich` -- **all absent**.

Also absent: `pandoc`, `perl` (which `latexmk` needs), `gs`. Present: `choco`,
`winget`, `python` 3.11.9.

Install directories checked and **not present**: `C:\texlive`,
`C:\Program Files\texlive`, `C:\Program Files\MiKTeX`,
`C:\Program Files (x86)\MiKTeX`, `C:\Users\Abhi\AppData\Local\Programs\MiKTeX`,
`C:\Users\Abhi\AppData\Roaming\MiKTeX`. No `latex`/`tex` Python packages in pip.

**WSL Ubuntu-24.04** (`command -v`, 9 binaries): `pdflatex`, `latexmk`, `tectonic`,
`xelatex`, `lualatex`, `tex`, `bibtex`, `biber`, `kpsewhich` -- **all absent**.
`dpkg -l | grep -iE 'tex|latex'` returns 20 lines, every one of them a false match on
the substring "tex" in the word "text" (`libtext-iconv-perl`, `groff-base`, `nano`,
etc.) -- **zero texlive packages**. No `/usr/share/texlive`, `/usr/share/texmf`,
`/opt/texlive`, or `/usr/local/texlive`.

So the zero-cost escape hatch -- "a texlive already in WSL would close this at no
cost" -- **does not exist**. The risk is real. It is just small.

Space: WSL root has 896 GB free. Windows `C:` has **24.5 GB free**, `I:` has 354.8 GB.
The 24.5 GB on `C:` is the binding constraint for any Windows-side install, and note
that the WSL disk image also lives on `C:` by default -- 144 MB is nothing against
that, but a full TeX Live (~7 GB) would be uncomfortable and is unnecessary here.

---

## 3. Source validation without a compiler: 0 blocking errors

Build tree, resolved from `paper/main.tex`, **8 files / 1514 lines / ~15,900 words**:

```
paper/main.tex                        80 lines
paper/sections/introduction.tex      185
paper/sections/related_work.tex      180
paper/sections/methods.tex           372
paper/sections/experiments.tex       190
paper/sections/discussion.tex        280
paper/sections/limitations.tex       153
paper/sections/conclusion.tex         74
```

Ten check classes were run by a purpose-written validator
(`<scratchpad>/texcheck2.py` and `bibcheck.py`; comment-aware, escape-aware,
math-mode-aware). Result: **0 ERROR**.

| # | Check | Result |
| --- | --- | --- |
| 1 | Every `\input` target exists | **6/6 resolve.** No nested `\input` inside sections. |
| 2 | Every `\cite` key resolves | **27/27 resolve.** 27 bib entries, 27 cited, 0 uncited, 0 duplicate keys. |
| 3 | Every `\ref` has a `\label`, and vice versa | **6 labels / 6 referenced, both directions clean.** No duplicates, no orphans. |
| 4 | Every `\includegraphics` target exists | **1/1 resolves** -- `{fig_achievable_roc}` -> `figures/fig_achievable_roc.pdf` via `\graphicspath{{../figures/}}`. |
| 5 | Brace balance, per file | **Balanced in all 8 files.** |
| 6 | Math delimiters `$`, `\[ \]`, `\( \)` | **Balanced.** No runaway inline math across a blank line. |
| 7 | `\begin`/`\end` environment nesting | **Balanced across the whole tree** (checked as one stack spanning files). |
| 8 | Undefined custom macros | **None.** Zero `\newcommand`/`\def`/`\DeclareMathOperator` in the entire tree, so nothing custom can be undefined. Every control sequence used is base LaTeX or from a loaded package. |
| 9 | Unescaped `_ ^ & #` in text mode | **None.** |
| 10 | plainnat required fields in the .bib | **0 issues.** 16 `@article` + 11 `@inproceedings`, all with author/title/journal-or-booktitle/year. Bib braces balanced. |

Two further notes on the source, both clean:

- **No non-ASCII characters anywhere in the tree.** This is the single most common
  silent killer of a first `pdflatex` run on a draft written in a modern editor
  (`\usepackage[utf8]{inputenc}` + `[T1]{fontenc}` cannot typeset `≤`, `×`, `—`, `→`
  and errors out with "Unicode character not set up for use with LaTeX"). The draft
  correctly uses `---`, `` `` ``/`''`, and math mode throughout. Zero occurrences.
- **Float internals are in the right order.** `discussion.tex:88-102` has
  `\includegraphics` -> `\caption` -> `\label`, and `experiments.tex:127-128` has
  `\caption` -> `\label`. Label-before-caption is a silent wrong-number bug that no
  compiler reports; it is not present.

### The 61 warnings are all benign, and I checked each class

- **40 x "bare `&`"** -- all at `experiments.tex:131-143`, all inside a well-formed
  `\begin{tabular}{lcccc}` ... `\end{tabular}`. Column arity verified separately:
  preamble declares 5 columns, every row has 4 ampersands = 5 cells. Correct.
  My validator flags `&` outside math without gating on tabular; these are its own
  false positives, not defects in the paper.
- **21 x "unescaped `%` in .bib"** -- all on `%`-prefixed comment lines outside any
  entry, plus `%TODO` inside two `annote` fields. `plainnat` does not emit `annote`,
  so these cannot reach the PDF. Harmless for the build (see section 4 for the
  content debt they represent).

An earlier version of the validator reported 10 errors. All 10 were its own bugs
(underscores inside `\[ ... \]` display math and inside `\includegraphics{...}` /
`\bibliography{...}` filename arguments). I fixed the validator and re-ran rather
than reporting them. Flagging this explicitly because a checker's false positives
reported as build errors would be exactly the wrong deliverable here.

---

## 4. Things that will not fail the build but should be on someone's list

These are content, not compilation. Listing them because they are the sort of thing a
first compile would have surfaced a month ago and has not.

1. **`paper/main.tex:12-13` -- `hyperref` is loaded before `natbib`.** The canonical
   order is `natbib` first. Modern `hyperref` patches around this at
   `\begin{document}` in most cases, so the likely worst outcome is citations that do
   not become clickable links, not a build failure. One-line fix (swap the two
   lines). **I did not make it -- another agent owns `paper/` right now.**
2. **Two of the three generated figures are never included.**
   `figures/fig1_ceiling.pdf` and `figures/fig2_censoring.pdf` exist (with `.png` and
   `_data.csv` siblings) but no `\includegraphics` references them. The paper
   currently ships **exactly one figure**, the achievable-ROC plot. Given that the
   surviving headline result is the granularity/false-alarm-floor finding, the
   ceiling and censoring figures being absent looks like an oversight rather than a
   decision.
3. **`experiments.tex:129-145` is an all-placeholder table.** Every data cell is
   `--`, pending the null-control run. The caption says so ("*Placeholder cells
   pending the definitive run*"). It will compile; it will compile as a table of
   dashes.
4. **Two unresolved `%TODO` verification markers in `related_work.bib`**
   (lines 142 and 196, plus 204), inside `annote` fields, flagging claims attributed
   to two references that were **not confirmable from the abstract** and need
   full-text verification before camera-ready. The .bib header (lines 3-7) flags this
   itself as VERIFY-BEFORE-SUBMIT. Invisible to the build, live for submission.
5. **arXiv does not run BibTeX.** The submission must include the generated
   `main.bbl`. Whenever the first successful build happens, keep the `.bbl` -- it is a
   required submission artifact, not a build intermediate.
6. `\author{ScriptSampler}`, affiliation deliberately omitted (`main.tex:22`), and
   `\date{\today}` will stamp the compile date. All intentional per the comments.

---

## 5. What this exercise cannot tell you, and how I priced it

**A static check is not a compile, and I am not reporting it as one.** The honest
statement is: the source is verified free of every error class that can be detected
without executing TeX, which covers the great majority of first-build failures on a
draft of this shape. The classes it structurally cannot see:

- package option clashes and load-order interactions beyond the one found in 4.1;
- font availability under the chosen `T1` encoding;
- `.bst` runtime behaviour on the 27 entries during the BibTeX pass;
- overfull/underfull boxes and float placement (cosmetic, never fatal);
- anything that depends on macro expansion order.

Weighing those against a 0-error static result on a draft with no custom macros, no
non-ASCII, no exotic packages (`amsmath`, `amssymb`, `graphicx`, `booktabs`,
`hyperref`, `natbib`, `geometry` -- all stock), and one figure: **I put the residual
at 0-45 minutes, and the probability that this becomes a multi-day problem at low.**
That estimate is on the source, which is measured. It is not a compile, which is not.

---

## 6. Options, priced. Your call -- I installed nothing.

**Option A -- WSL apt (recommended; cheapest and best-measured).**
Measured with `apt-get install --print-uris` / `-s`, which downloads and installs
nothing:

- `texlive-latex-base texlive-latex-recommended texlive-fonts-recommended`
- **49.1 MB download, 21 packages, 144 MB on disk.** ~5 min on a normal connection.
- Coverage verified against the paper's actual `\usepackage` list: `natbib`,
  `geometry`, `graphics`, `hyperref`, `amsmath`, `amscls`, `url`, `psnfss` are in
  `texlive-latex-base`; `booktabs` is in `texlive-latex-recommended`; T1 fonts in
  `texlive-fonts-recommended`. Nothing the paper uses falls outside this set.
- For reference, adding `texlive-latex-extra texlive-bibtex-extra` for future
  headroom: 164.7 MB download, 33 packages. **Not needed for this paper.**
- Then: `cd /mnt/i/GITHUBPROJECTS/SE\ Research/paper && pdflatex main && bibtex main
  && pdflatex main && pdflatex main`.
- Caveat: this runs `apt` inside the same distro as the live GPU run. `apt` is
  CPU-only and touches nothing under `scripts/`, but it does take the dpkg lock, so
  worth doing at a moment you are comfortable with.

**Option B -- Tectonic (single binary, no package manager, no admin).**
Not in Ubuntu's apt (`apt-cache policy tectonic` returns nothing), so this is a
GitHub release download on the Windows side. Roughly 25 MB for the zip, plus
on-demand package downloads cached on first run (a few hundred MB, one time).
**Sizes here are approximate -- unlike Option A I could not measure them locally.**
First build a few minutes, subsequent builds seconds. Runs the XeTeX engine, so the
`inputenc` line becomes a harmless no-op. Handles the BibTeX passes automatically.

**Option C -- Overleaf (zero install).** Upload `paper/` plus `figures/`. Costs
nothing on this machine and needs no permission from anyone. Downside: the source
then lives in two places during the last 27 days before a deadline, and the repo is
the system of record. Reasonable as a **verification** step -- one upload confirms the
build today -- and poor as the ongoing workflow.

**Not recommended: MiKTeX or full TeX Live on Windows.** MiKTeX basic is ~250 MB and
TeX Live is ~7 GB, against 24.5 GB free on `C:`. Both are strictly more expensive
than Option A for no benefit here.

---

## 7. Reproducing this, and the standing check left behind

The audit is now a re-runnable guard rather than a one-off:

```
python scripts/check_latex_source.py     # exit 0 = no blocking errors, 1 = errors
```

`scripts/check_latex_source.py` (new, added by this audit) runs all ten check classes
plus the plainnat required-field pass in one command. It is pure Python 3.11 with no
dependencies, resolves paths relative to the repo root so it works from anywhere, and
reads the repo read-only. It exits non-zero on any ERROR, so it can be wired into the
pre-submission checklist next to the existing operational checkers.

Current output: **0 ERROR, 4 WARN** -- the four being the `%TODO` markers inside
`annote` fields covered in section 4.4, which `plainnat` never emits.

Worth re-running after any edit to `paper/`, and in particular right before the
arXiv upload, since it catches the two failure modes most likely to be introduced
during a final editing pass: a `\cite` key that no longer resolves, and a non-ASCII
character pasted in from a browser or a review comment.

Nothing in `paper/` was modified. Nothing was installed. No GPU work was run. No
commit, stash, or checkout was made -- `scripts/check_latex_source.py` and this file
are left uncommitted in the working tree.
