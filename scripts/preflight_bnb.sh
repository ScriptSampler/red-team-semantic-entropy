#!/bin/bash
# Pre-flight: check whether upstream bitsandbytes supports 4-bit quantisation
# on RX 9070 XT (gfx1201). If it does, the project plan (Llama 3.1 8B at 4-bit
# with N=10 sampling) is unblocked. If it doesn't, we'd switch to an AWQ
# or GPTQ pre-quantised model via autoawq or auto-gptq.
set -uo pipefail

PROJECT_DIR="/mnt/i/GITHUBPROJECTS/SE Research"
cd "$PROJECT_DIR"
source .venv-wsl/bin/activate

echo "=== 1. Install upstream bitsandbytes (latest) ==="
pip install --upgrade 'bitsandbytes>=0.45' 2>&1 | tail -8

echo
echo "=== 2. Import + check ROCm detection ==="
python <<'PY'
import sys
try:
    import bitsandbytes as bnb
    print("bnb version:", bnb.__version__)
    print("bnb file:", bnb.__file__)
    try:
        from bitsandbytes import cuda_setup
        print("cuda_setup module:", cuda_setup)
    except Exception as e:
        print("cuda_setup import:", e)
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
echo "=== 4. Load a tiny non-gated model in 4-bit via transformers ==="
# Qwen2.5-0.5B is small (around 500 MB), non-gated, instruction-tuned.
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
echo "All four steps printed without FAILED: bitsandbytes 4-bit works on gfx1201."
echo "Step 2 failed: upstream bnb doesn't auto-detect ROCm. Try the AMD fork or AWQ."
echo "Steps 3 or 4 failed: detected but kernels don't run. Try the AMD fork or AWQ."
