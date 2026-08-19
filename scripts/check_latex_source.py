# -*- coding: utf-8 -*-
"""Compiler-free static validation, v2: math-aware specials, tabular arity, bib syntax."""
import os, re, sys, unicodedata, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAPER = os.path.join(ROOT, "paper")
MAIN = os.path.join(PAPER, "main.tex")
FIGDIRS = [os.path.join(ROOT, "figures"), os.path.join(PAPER, "figures")]

problems = []
def P(sev, f, ln, msg): problems.append((sev, f, ln, msg))

def strip_comments(line):
    out = []; i = 0
    while i < len(line):
        c = line[i]
        if c == "\\" and i + 1 < len(line):
            out.append(line[i:i+2]); i += 2; continue
        if c == "%":
            return "".join(out)
        out.append(c); i += 1
    return "".join(out)

files = []
def load(rel, ab):
    with open(ab, "r", encoding="utf-8", errors="surrogateescape") as f:
        raw = f.read().split("\n")
    files.append((rel, ab, raw)); return raw

main_raw = load("paper/main.tex", MAIN)
for ln, line in enumerate(main_raw, 1):
    for m in re.finditer(r"\\(input|include)\s*\{([^}]*)\}", strip_comments(line)):
        tgt = m.group(2).strip(); cand = os.path.join(PAPER, tgt); found = None
        for c in (cand, cand + ".tex"):
            if os.path.isfile(c): found = c; break
        if found is None:
            P("ERROR", "paper/main.tex", ln, "\\%s{%s}: file does not exist" % (m.group(1), tgt))
        else:
            load("paper/" + tgt + ("" if tgt.endswith(".tex") else ".tex"), found)

codelines = {rel: [(i, strip_comments(l)) for i, l in enumerate(raw, 1)]
             for rel, ab, raw in files}

def pairs():
    for rel, _, _ in files:
        for ln, code in codelines[rel]:
            yield rel, ln, code

# ---- global math mask, tracking $, \[ \], \( \), and math environments ----
MATH_ENVS = {"equation","equation*","align","align*","gather","gather*","aligned",
             "split","cases","array","eqnarray","eqnarray*","multline","multline*",
             "displaymath","math","alignat","alignat*"}
ARG_CMDS = ("input","include","includegraphics","bibliography","bibliographystyle",
            "label","ref","eqref","autoref","pageref","nameref","cref","Cref",
            "cite","citep","citet","citealp","citealt","citeauthor","citeyear",
            "citeyearpar","nocite","url","href","graphicspath","usepackage",
            "documentclass","hypersetup","lstinline","verb","texttt","path")

def build_masks(rel):
    """Return dict lineno -> (mathmask, argmask)."""
    res = {}
    indollar = False; disp = 0; paren = 0; envdepth = 0
    for ln, code in codelines[rel]:
        # arg mask: braces belonging to filename/key-taking commands
        argmask = [False]*len(code)
        for m in re.finditer(r"\\(" + "|".join(ARG_CMDS) + r")\s*(?:\[[^\]]*\])?\s*\{", code):
            j = m.end() - 1; depth = 0
            while j < len(code):
                if code[j] == "\\": j += 2; continue
                if code[j] == "{": depth += 1
                elif code[j] == "}":
                    depth -= 1
                    if depth == 0: argmask[m.start():j+1] = [True]*(j+1-m.start()); break
                j += 1
        mathmask = [False]*len(code)
        i = 0
        while i < len(code):
            if code[i] == "\\":
                nxt = code[i+1:i+2]
                if nxt == "[": disp += 1
                elif nxt == "]": disp = max(0, disp-1)
                elif nxt == "(": paren += 1
                elif nxt == ")": paren = max(0, paren-1)
                bm = indollar or disp > 0 or paren > 0 or envdepth > 0
                mathmask[i] = bm
                if i+1 < len(code): mathmask[i+1] = bm
                i += 2; continue
            if code[i] == "$":
                indollar = not indollar
                mathmask[i] = True; i += 1; continue
            mathmask[i] = indollar or disp > 0 or paren > 0 or envdepth > 0
            i += 1
        for m in re.finditer(r"\\begin\s*\{([^}]*)\}", code):
            if m.group(1) in MATH_ENVS: envdepth += 1
        for m in re.finditer(r"\\end\s*\{([^}]*)\}", code):
            if m.group(1) in MATH_ENVS: envdepth = max(0, envdepth-1)
        res[ln] = (mathmask, argmask)
    return res

masks = {rel: build_masks(rel) for rel, _, _ in files}

CELL_ENVS = {"tabular", "tabular*", "tabularx", "array", "matrix", "pmatrix",
             "bmatrix", "vmatrix", "Vmatrix", "align", "align*", "aligned",
             "alignat", "alignat*", "cases", "split", "eqnarray", "eqnarray*"}
for rel, _, _ in files:
    celldepth = 0
    for ln, code in codelines[rel]:
        for m in re.finditer(r"\\begin\s*\{([^}]*)\}", code):
            if m.group(1) in CELL_ENVS: celldepth += 1
        mm, am = masks[rel][ln]
        for i, c in enumerate(code):
            if c not in "_^&#": continue
            if mm[i] or am[i]: continue
            if i > 0 and code[i-1] == "\\": continue
            snip = code[max(0,i-40):i+40].strip()
            if c in "_^":
                P("ERROR", rel, ln, "unescaped '%s' in text mode (Missing $ inserted) | %s" % (c, snip))
            elif c == "&" and celldepth == 0:
                P("WARN", rel, ln, "bare '&' outside tabular/math | %s" % snip)
            elif c == "#":
                P("WARN", rel, ln, "bare '#' | %s" % snip)
        for m in re.finditer(r"\\end\s*\{([^}]*)\}", code):
            if m.group(1) in CELL_ENVS: celldepth = max(0, celldepth-1)

# ---- tabular arity ----
for rel, _, _ in files:
    intab = None
    for ln, code in codelines[rel]:
        m = re.search(r"\\begin\s*\{tabular\}\s*(?:\[[^\]]*\])?\s*\{([^}]*)\}", code)
        if m:
            spec = re.sub(r"[^clrpXmb|@*><]", "", m.group(1))
            ncol = len(re.findall(r"[clrXpmb]", m.group(1)))
            intab = (ln, ncol, m.group(1)); rowbuf = ""
            continue
        if intab and re.search(r"\\end\s*\{tabular\}", code):
            intab = None; continue
        if intab:
            if re.match(r"\s*\\(hline|toprule|midrule|bottomrule|cmidrule|addlinespace)", code.strip()):
                continue
            if code.strip() == "": continue
            mm, am = masks[rel][ln]
            amp = sum(1 for i, c in enumerate(code) if c == "&" and not mm[i]
                      and not (i > 0 and code[i-1] == "\\"))
            if "\\\\" in code and amp and amp + 1 != intab[1]:
                if not re.search(r"\\multicolumn", code):
                    P("WARN", rel, ln, "tabular row has %d cells, preamble '%s' declares %d"
                      % (amp+1, intab[2], intab[1]))
    if intab:
        P("ERROR", rel, intab[0], "\\begin{tabular} never closed")

# ---- bib syntax ----
bibpath = os.path.join(PAPER, "related_work.bib")
bibkeys = set()
with open(bibpath, "r", encoding="utf-8", errors="surrogateescape") as f:
    bibraw = f.read()
biblines = bibraw.split("\n")
depth = 0; entry_start = None; entry_key = None
for ln, line in enumerate(biblines, 1):
    m = re.match(r"\s*@\s*(\w+)\s*[{(]\s*([^,\s}]*)", line)
    if m and depth == 0:
        if m.group(1).lower() not in ("comment","preamble","string"):
            entry_start, entry_key = ln, m.group(2)
            if entry_key in bibkeys:
                P("ERROR", "paper/related_work.bib", ln, "duplicate entry key '%s'" % entry_key)
            bibkeys.add(entry_key)
    i = 0
    while i < len(line):
        if line[i] == "\\": i += 2; continue
        if line[i] == "{": depth += 1
        elif line[i] == "}":
            depth -= 1
            if depth < 0:
                P("ERROR", "paper/related_work.bib", ln, "unmatched '}' in bib")
                depth = 0
        i += 1
if depth != 0:
    P("ERROR", "paper/related_work.bib", entry_start or 0,
      "%d unclosed brace(s) in .bib; last entry opened was '%s'" % (depth, entry_key))
# unescaped % and & inside bib field values (only where they can reach LaTeX:
# inside an entry. A '%' on a line outside any entry is an ignored bib comment.)
_d = 0
for ln, line in enumerate(biblines, 1):
    i = 0
    while i < len(line):
        c = line[i]
        if c == "\\": i += 2; continue
        if c == "{": _d += 1
        elif c == "}": _d = max(0, _d - 1)
        elif c in "%&" and _d > 0:
            P("WARN", "paper/related_work.bib", ln,
              "unescaped '%s' inside a bib entry | %s" % (c, line.strip()[:70]))
        i += 1

# ---- citations / labels / graphics / braces / envs (as v1) ----
cited = {}
for rel, ln, code in pairs():
    for m in re.finditer(r"\\(?:no)?cite[a-zA-Z]*\s*(?:\[[^\]]*\]\s*){0,2}\{([^}]*)\}", code):
        for k in m.group(1).split(","):
            k = k.strip()
            if k: cited.setdefault(k, []).append((rel, ln))
for k in sorted(cited):
    if k not in bibkeys:
        for rel, ln in cited[k]:
            P("ERROR", rel, ln, "\\cite{%s}: key absent from related_work.bib" % k)

labels = {}; refs = {}
for rel, ln, code in pairs():
    for m in re.finditer(r"\\label\s*\{([^}]*)\}", code):
        labels.setdefault(m.group(1).strip(), []).append((rel, ln))
    for m in re.finditer(r"\\(?:eqref|autoref|pageref|nameref|Cref|cref|ref)\s*\{([^}]*)\}", code):
        for k in m.group(1).split(","):
            k = k.strip()
            if k: refs.setdefault(k, []).append((rel, ln))
for k in sorted(refs):
    if k not in labels:
        for rel, ln in refs[k]:
            P("ERROR", rel, ln, "\\ref{%s}: no matching \\label" % k)
for k in sorted(labels):
    if len(labels[k]) > 1:
        P("ERROR", labels[k][1][0], labels[k][1][1],
          "duplicate \\label{%s} (first at %s:%d)" % (k, labels[k][0][0], labels[k][0][1]))

figs_used = []
for rel, ln, code in pairs():
    for m in re.finditer(r"\\includegraphics\s*(?:\[[^\]]*\])?\s*\{([^}]*)\}", code):
        tgt = m.group(1).strip(); hits = []
        for b in [os.path.join(PAPER, tgt)] + [os.path.join(d, tgt) for d in FIGDIRS]:
            if os.path.splitext(b)[1] and os.path.isfile(b): hits.append(b)
            for e in (".pdf",".png",".jpg",".jpeg",".eps"):
                if os.path.isfile(b + e): hits.append(b + e)
        figs_used.append((rel, ln, tgt, hits[0] if hits else None))
        if not hits:
            P("ERROR", rel, ln, "\\includegraphics{%s}: not found (graphicspath ../figures/, figures/)" % tgt)

for rel, _, _ in files:
    depth = 0; opens = []
    for ln, code in codelines[rel]:
        i = 0
        while i < len(code):
            if code[i] == "\\": i += 2; continue
            if code[i] == "{": depth += 1; opens.append(ln)
            elif code[i] == "}":
                depth -= 1
                if depth < 0: P("ERROR", rel, ln, "unmatched '}'"); depth = 0
                elif opens: opens.pop()
            i += 1
    if depth: P("ERROR", rel, opens[0] if opens else 0,
                "%d unclosed '{'; earliest at line %s" % (depth, opens[0] if opens else "?"))

# math delimiter balance across whole doc
tot_dollar = 0
for rel, _, _ in files:
    indollar = False; start = None; disp = []; paren = []
    for ln, code in codelines[rel]:
        i = 0
        while i < len(code):
            if code[i] == "\\":
                n = code[i+1:i+2]
                if n == "[": disp.append(ln)
                elif n == "]":
                    if disp: disp.pop()
                    else: P("ERROR", rel, ln, "\\] with no matching \\[")
                elif n == "(": paren.append(ln)
                elif n == ")":
                    if paren: paren.pop()
                    else: P("ERROR", rel, ln, "\\) with no matching \\(")
                i += 2; continue
            if code[i] == "$":
                indollar = not indollar
                if indollar: start = ln
                i += 1; continue
            i += 1
        if indollar and code.strip() == "":
            P("ERROR", rel, start, "runaway inline math: $ opened here, blank line at %d" % ln)
            indollar = False
    if indollar: P("ERROR", rel, start, "unclosed inline math $")
    for ln in disp: P("ERROR", rel, ln, "unclosed \\[")
    for ln in paren: P("ERROR", rel, ln, "unclosed \\(")

envstack = []
for rel, ln, code in pairs():
    toks = []
    for m in re.finditer(r"\\begin\s*\{([^}]*)\}", code): toks.append((m.start(), "b", m.group(1)))
    for m in re.finditer(r"\\end\s*\{([^}]*)\}", code): toks.append((m.start(), "e", m.group(1)))
    for _, kind, name in sorted(toks):
        if kind == "b": envstack.append((name, rel, ln))
        else:
            if not envstack: P("ERROR", rel, ln, "\\end{%s} with nothing open" % name)
            elif envstack[-1][0] != name:
                nm, r0, l0 = envstack.pop()
                P("ERROR", rel, ln, "\\end{%s} closes \\begin{%s} from %s:%d" % (name, nm, r0, l0))
            else: envstack.pop()
for nm, r0, l0 in envstack:
    P("ERROR", r0, l0, "\\begin{%s} never closed" % nm)

# ---- bib required fields (plainnat) ----
REQ = {
    "article":       ["author", "title", "journal", "year"],
    "book":          ["author|editor", "title", "publisher", "year"],
    "inproceedings": ["author", "title", "booktitle", "year"],
    "incollection":  ["author", "title", "booktitle", "publisher", "year"],
    "techreport":    ["author", "title", "institution", "year"],
    "phdthesis":     ["author", "title", "school", "year"],
    "mastersthesis": ["author", "title", "school", "year"],
    "unpublished":   ["author", "title", "note"],
    "inbook":        ["author|editor", "title", "chapter|pages", "publisher", "year"],
    "proceedings":   ["title", "year"],
    "misc": [], "booklet": ["title"], "manual": ["title"],
}
_i = 0
_ent = re.compile(r"@\s*(\w+)\s*\{\s*([^,\s}]+)\s*,", re.S)
while True:
    _m = _ent.search(bibraw, _i)
    if not _m: break
    _type, _key = _m.group(1).lower(), _m.group(2)
    _j = _m.end(); _d = 1
    while _j < len(bibraw) and _d > 0:
        if bibraw[_j] == "\\": _j += 2; continue
        if bibraw[_j] == "{": _d += 1
        elif bibraw[_j] == "}": _d -= 1
        _j += 1
    _body = bibraw[_m.end():_j-1]
    _ln = bibraw[:_m.start()].count("\n") + 1
    _i = _j
    if _type in ("comment", "preamble", "string"): continue
    _fields = set(f.lower() for f in re.findall(r"(?m)^\s*(\w+)\s*=", _body))
    if _type not in REQ:
        P("WARN", "paper/related_work.bib", _ln, "unknown entry type @%s for '%s'" % (_type, _key))
        continue
    for _spec in REQ[_type]:
        if not any(a in _fields for a in _spec.split("|")):
            P("WARN", "paper/related_work.bib", _ln,
              "@%s{%s}: missing plainnat-required field '%s'" % (_type, _key, _spec))

# ---- report ----
o = []
def w(s=""): o.append(s)
w("FILES: " + ", ".join("%s(%d)" % (r.split('/')[-1], len(x)) for r, a, x in files))
w("BIB entries: %d; distinct keys cited: %d; uncited: %d"
  % (len(bibkeys), len(cited), len(bibkeys - set(cited))))
w("LABELS: %d defined / %d referenced" % (len(labels), len(refs)))
w("FIGURES:")
for rel, ln, tgt, hit in figs_used:
    w("  %s:%d  {%s} -> %s" % (rel, ln, tgt, hit or "*** MISSING ***"))
w()
errs = [p for p in problems if p[0] == "ERROR"]
warns = [p for p in problems if p[0] == "WARN"]
w("PROBLEMS: %d ERROR, %d WARN" % (len(errs), len(warns)))
for sev, f, ln, msg in errs + warns:
    w("  [%s] %s:%s  %s" % (sev, f, ln, msg))
sys.stdout.buffer.write(("\n".join(o) + "\n").encode("utf-8", "replace"))
sys.exit(1 if errs else 0)
