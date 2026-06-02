#!/bin/bash
# Diagnose WSL DNS, specifically for the HuggingFace Xet backend.
echo "=== /etc/resolv.conf ==="
cat /etc/resolv.conf

echo
echo "=== resolve huggingface.co ==="
getent hosts huggingface.co || echo "FAILED"

echo
echo "=== resolve cas-bridge.xethub.hf.co (Xet backend) ==="
getent hosts cas-bridge.xethub.hf.co || echo "FAILED"

echo
echo "=== resolve cdn-lfs.huggingface.co (classic CDN) ==="
getent hosts cdn-lfs.huggingface.co || echo "FAILED"

echo
echo "=== EXIT_CODE from the failed run ==="
grep "EXIT_CODE" "/mnt/i/GITHUBPROJECTS/SE Research/results/wk2_mon_run.log" || echo "no exit code line"

echo
echo "=== partial shards already in cache? ==="
find ~/.cache/huggingface -name "*.safetensors*" 2>/dev/null | head
du -sh ~/.cache/huggingface 2>/dev/null || echo "no cache yet"
