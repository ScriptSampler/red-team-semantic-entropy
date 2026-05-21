#!/bin/bash
# Pre-flight: try bitsandbytes 4-bit on RX 9070 XT (gfx1201) via upstream pip install.
# If upstream lacks ROCm support / errors on import, we know we need the source build path.
set -uo pipefail

PROJECT_DIR="/mnt/i/GITHUBPROJECTS/SE Research"
cd "$PROJECT_DIR"
source .venv-wsl/bin/activate

echo "=== 1. Install upstream bitsandbytes (latest) ==="
pip install --upgrade 'bitsandbytes>=0.45' 2>&1 | tail -8

echo
echo "=== 2. Import + check ROCm detection ==="
python <<'PY'
import importlib, sys
try:
    import bitsandbytes as bnb
    print("bnb version:", bnb.__version__)
    print("bnb file:", bnb.__file__)
    # Check if ROCm backend is registered
    try:
        from bitsandbytes import cuda_setup
        print("cuda_setup module:", cuda_setup)
    except Exception as e:
        print("cuda_setup import:", e)
    # Try to print the device the lib detects
    try:
        info = bnb.utils.print_module_info() if hasattr(bnb.utils, 'print_module_info') else None
    except Exception as e:
        print("module_info err:", e)
    # Most-direct check: try to import the c-extension
    print("backends:", getattr(bnb, 'backends', 'no backends attr'))
except Exception as e:
    print("bnb import FAILED:", type(e).__name__, str(e)[:300])
    sys.exit(2)
PY
echo "import exit: $?"

echo
echo "=== 3. Quick 4-bit linear test on cuda (no model load) ==="
python <<'PY'
import sys
try:
    import torch
    import bitsandbytes as bnb
    print("torch cuda:", torch.cuda.is_available(), "device:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "none")
    # Tiny 4-bit linear layer test
    from bitsandbytes.nn import Linear4bit
    layer = Linear4bit(128, 64, bias=False, quant_type='nf4').to('cuda')
    x = torch.randn(2, 128, device='cuda', dtype=torch.float16)
    y = layer(x)
    print("Linear4bit forward OK:", y.shape, y.dtype, "mem MB:", torch.cuda.memory_allocated()/1024**2)
except Exception as e:
    print("4bit linear FAILED:", type(e).__name__, str(e)[:500])
    sys.exit(3)
PY
echo "linear4bit exit: $?"

echo
echo "=== 4. Try loading a tiny non-gated model in 4-bit via transformers ==="
# Qwen2.5-0.5B is small (~500MB), non-gated, instruction-tuned
python <<'PY'
import sys
try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    model_id = "Qwen/Qwen2.5-0.5B-Instruct"
    bnb_cfg = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type='nf4',
                                  bnb_4bit_compute_dtype=torch.float16)
    tok = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForCausalLM.from_pretrained(model_id, quantization_config=bnb_cfg,
                                                  device_map='cuda', torch_dtype=torch.float16)
    print("Loaded 4-bit model:", model.config.model_type, "device:", next(model.parameters()).device)
    inputs = tok("The capital of France is", return_tensors='pt').to('cuda')
    out = model.generate(**inputs, max_new_tokens=10, do_sample=False)
    text = tok.decode(out[0], skip_special_tokens=True)
    print("Generated:", repr(text))
    print("Peak mem MB:", torch.cuda.max_memory_allocated()/1024**2)
except Exception as e:
    print("model load FAILED:", type(e).__name__, str(e)[:500])
    sys.exit(4)
PY
echo "model load exit: $?"

echo
echo "=== Verdict ==="
echo "If all 4 steps printed without FAILED: bitsandbytes 4-bit works on gfx1201 — proceed with plan."
echo "If step 2 fails: bitsandbytes-rocm not auto-detected by upstream → need source build or fork."
echo "If step 3/4 fails: detected but kernels don't run → try AMD fork or pivot to AWQ."
