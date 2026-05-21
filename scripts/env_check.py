"""Week 1 deliverable: environment smoke test.

Run inside the WSL .venv-wsl. Reports torch/ROCm versions, GPU detection,
basic kernel execution, VRAM allocation. Writes the report to results/env_check.txt
so we have a tagged artifact for the env-ready commit.
"""
from __future__ import annotations

import os
import sys
import platform
import subprocess
from pathlib import Path
from datetime import datetime


def section(title: str) -> str:
    return f"\n=== {title} ===\n"


def run(cmd: list[str]) -> str:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return (out.stdout + out.stderr).strip()
    except Exception as e:
        return f"<error running {cmd}: {e}>"


def main() -> int:
    lines: list[str] = []
    lines.append(f"# env_check report — {datetime.utcnow().isoformat()}Z")
    lines.append(f"Host: {platform.platform()}")
    lines.append(f"Python: {sys.version.split()[0]} at {sys.executable}")

    lines.append(section("rocminfo (GPU agents)"))
    rocminfo = run(["rocminfo"])
    for line in rocminfo.splitlines():
        if any(k in line for k in ("Agent ", "Name:", "Marketing Name:", "Compute Unit:", "Wavefront Size:", "gfx1")):
            lines.append(line)

    lines.append(section("torch import"))
    try:
        import torch
        lines.append(f"torch: {torch.__version__}")
        lines.append(f"torch.version.cuda: {torch.version.cuda}")
        lines.append(f"torch.version.hip: {torch.version.hip}")
        lines.append(f"torch.cuda.is_available(): {torch.cuda.is_available()}")
        lines.append(f"torch.cuda.device_count(): {torch.cuda.device_count()}")
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                lines.append(f"  device[{i}]: {torch.cuda.get_device_name(i)}")
                props = torch.cuda.get_device_properties(i)
                lines.append(f"    total_mem_GB: {props.total_memory / 1024**3:.2f}")
                lines.append(f"    multi_processor_count: {props.multi_processor_count}")
                lines.append(f"    major.minor: {props.major}.{props.minor}")
    except Exception as e:
        lines.append(f"torch import FAILED: {e}")
        return write_and_exit(lines, 1)

    lines.append(section("matmul on GPU"))
    if not torch.cuda.is_available():
        lines.append("torch.cuda.is_available() False — cannot run GPU matmul.")
        return write_and_exit(lines, 2)
    try:
        device = torch.device("cuda")
        x = torch.randn(2048, 2048, device=device, dtype=torch.float32)
        y = torch.randn(2048, 2048, device=device, dtype=torch.float32)
        torch.cuda.synchronize()
        import time
        t0 = time.perf_counter()
        z = (x @ y).sum().item()
        torch.cuda.synchronize()
        dt = time.perf_counter() - t0
        lines.append(f"2048x2048 fp32 matmul → sum={z:.4f}  ({dt*1000:.2f} ms)")
        mem_mb = torch.cuda.memory_allocated(device) / 1024**2
        lines.append(f"memory_allocated: {mem_mb:.2f} MB")
        mem_max_mb = torch.cuda.max_memory_allocated(device) / 1024**2
        lines.append(f"max_memory_allocated: {mem_max_mb:.2f} MB")
    except Exception as e:
        lines.append(f"GPU matmul FAILED: {e}")
        return write_and_exit(lines, 3)

    lines.append(section("transformers + datasets import"))
    try:
        import transformers
        import datasets
        lines.append(f"transformers: {transformers.__version__}")
        lines.append(f"datasets: {datasets.__version__}")
    except Exception as e:
        lines.append(f"FAILED: {e}")
        return write_and_exit(lines, 4)

    lines.append(section("Result"))
    lines.append("PASS — env-ready.")
    return write_and_exit(lines, 0)


def write_and_exit(lines: list[str], code: int) -> int:
    text = "\n".join(lines) + "\n"
    out_path = Path(__file__).resolve().parent.parent / "results" / "env_check.txt"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text)
    print(text)
    print(f"\nWritten to {out_path}", file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
