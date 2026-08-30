#!/usr/bin/env python3
"""A minimal MCP server exposing Google's Gemini API as a tool.

WHY THIS EXISTS. Every reviewer of this paper so far has been a Claude agent, which
means they share one model's priors and one model's blind spots. Two of the three most
serious findings in the 2026-08-30 panel were cases of the paper asserting something its
own Table 1 contradicts -- exactly what a fresh reader catches and a familiar one does
not. A second model is not a nicety here; it is the only source of genuinely independent
error in the review loop.

DESIGN. Speaks MCP over stdio as JSON-RPC 2.0. Standard library only: no pip install, no
lockfile, no supply chain. Reads the API key from the environment so it never appears in
a config file, a shell history, or this repository.

SETUP
-----
1. Get an API key from https://aistudio.google.com/apikey
   Note: a Gemini *Pro subscription* does NOT grant API access. They are different
   products. The API key is separate and free-tier eligible.

2. Register the server (run this in an interactive terminal; a non-interactive Claude
   session cannot do it for you):

     claude mcp add gemini \
       --env GEMINI_API_KEY=your_key_here \
       --env GEMINI_MODEL=gemini-2.5-pro \
       -- python "I:/GITHUBPROJECTS/SE Research/tools/gemini_mcp.py"

   Check the current model id in AI Studio before pinning it; the default below is a
   guess at the naming and is deliberately overridable.

3. Verify: `claude mcp list` should show `gemini`, and the tool `ask_gemini` becomes
   callable. Test it standalone first:

     GEMINI_API_KEY=... python tools/gemini_mcp.py --selftest "Reply with the word OK."

PRIVACY. `ask_gemini` sends whatever you pass it to Google. For a preprint you intend to
post publicly that is unremarkable, but it is a real egress and worth one deliberate
thought before sending anything you would not put on arXiv.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-pro")
API_KEY = os.environ.get("GEMINI_API_KEY", "")
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
MAX_CHARS = 700_000  # generous, but bounded: a truncated prompt beats an opaque 400.


def _extract_text(path: str) -> str:
    """Return the text of a file. PDFs go through pdftotext if it is available."""
    if path.lower().endswith(".pdf"):
        for exe in ("pdftotext", "/usr/bin/pdftotext"):
            try:
                out = subprocess.run(
                    [exe, "-layout", path, "-"],
                    capture_output=True, text=True, timeout=120,
                )
                if out.returncode == 0 and out.stdout.strip():
                    return out.stdout
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        raise RuntimeError(
            f"{path} is a PDF and pdftotext is not available on PATH. "
            "Install poppler-utils, or pass the .tex sources instead."
        )
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def call_gemini(prompt: str, files: list[str] | None = None, system: str = "") -> str:
    if not API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Get a key at https://aistudio.google.com/apikey "
            "-- note that a Gemini Pro subscription is a different product and does not "
            "grant API access."
        )

    parts = []
    for path in files or []:
        text = _extract_text(path)
        parts.append(f"===== FILE: {os.path.basename(path)} =====\n{text}\n===== END =====")
    parts.append(prompt)
    body_text = "\n\n".join(parts)

    truncated = False
    if len(body_text) > MAX_CHARS:
        body_text = body_text[:MAX_CHARS]
        truncated = True

    payload = {"contents": [{"role": "user", "parts": [{"text": body_text}]}]}
    if system:
        payload["systemInstruction"] = {"parts": [{"text": system}]}

    req = urllib.request.Request(
        ENDPOINT.format(model=MODEL) + f"?key={API_KEY}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:1500]
        raise RuntimeError(f"Gemini returned HTTP {e.code}. Body: {detail}") from None
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach the Gemini API: {e.reason}") from None

    try:
        out = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        # Surface the raw response rather than a confident empty answer: a blocked or
        # empty candidate is information, and silently returning "" would be a lie.
        return "NO TEXT RETURNED. Raw response:\n" + json.dumps(data, indent=2)[:4000]

    if truncated:
        out = (f"[NOTE: input was truncated to {MAX_CHARS} characters before sending. "
               f"The reply below may not reflect the whole document.]\n\n") + out
    return out


TOOLS = [{
    "name": "ask_gemini",
    "description": (
        "Send a prompt, optionally with the contents of local files, to Google's Gemini "
        "and return its reply. Use it for a genuinely independent second opinion -- a "
        "review, a critique, a check of reasoning -- where a different model's blind "
        "spots are the point. PDFs are converted with pdftotext. Everything sent goes to "
        "Google."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "prompt": {"type": "string", "description": "The question or instruction."},
            "files": {
                "type": "array", "items": {"type": "string"},
                "description": "Absolute paths to include verbatim before the prompt.",
            },
            "system": {"type": "string", "description": "Optional system instruction."},
        },
        "required": ["prompt"],
    },
}]


def respond(rid, result=None, error=None):
    msg = {"jsonrpc": "2.0", "id": rid}
    if error is not None:
        msg["error"] = error
    else:
        msg["result"] = result
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue

        method, rid = msg.get("method"), msg.get("id")

        if method == "initialize":
            respond(rid, {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "gemini", "version": "1.0.0"},
            })
        elif method == "tools/list":
            respond(rid, {"tools": TOOLS})
        elif method == "tools/call":
            params = msg.get("params", {})
            args = params.get("arguments", {}) or {}
            if params.get("name") != "ask_gemini":
                respond(rid, error={"code": -32601, "message": f"Unknown tool {params.get('name')}"})
                continue
            try:
                text = call_gemini(args.get("prompt", ""), args.get("files"), args.get("system", ""))
                respond(rid, {"content": [{"type": "text", "text": text}]})
            except Exception as exc:
                respond(rid, {"content": [{"type": "text", "text": f"ERROR: {exc}"}], "isError": True})
        elif rid is not None:
            respond(rid, error={"code": -32601, "message": f"Unknown method {method}"})
        # Notifications (no id) are ignored, per JSON-RPC.


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--selftest":
        print(call_gemini(sys.argv[2]))
    else:
        main()
