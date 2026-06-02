# Week 2 Mon: Llama 3.1 8B Instruct, 4-bit load + generation
GPU: AMD Radeon RX 9070 XT
Total VRAM: 15.81 GB

## Load (downloads on first run)
model: meta-llama/Llama-3.1-8B-Instruct
quant: 4-bit nf4, double_quant=True, compute=torch.bfloat16
load time: 54.3 s
VRAM after load: 5440 MB (5.31 GB)

## Greedy single-answer generation
Q: What is the capital of France?
A: 'The capital of France is Paris.'  (1.14 s)

Q: Who wrote the novel Pride and Prejudice?
A: 'The novel "Pride and Prejudice" was written by Jane Austen.'  (1.05 s)

Q: What year did the first human land on the Moon?
A: 'The first humans landed on the Moon in 1969. Specifically, it was on July 20, 1969, when NASA\'s Apollo 11 mission successfully landed astronauts Neil Armstrong and Edwin "Buzz" Aldrin on the lunar surface'  (2.40 s)

## N-sample generation (the SE sampling step)
Q: What is the capital of Australia?
N=10 samples at T=1.0 in 2.20 s (0.22 s/sample):
  [0] 'The capital of Australia is Canberra.'
  [1] 'The capital of Australia is Canberra.'
  [2] 'The capital of Australia is Canberra.'
  [3] 'The capital of Australia is Canberra.'
  [4] 'The capital of Australia is Canberra.'
  [5] 'The capital of Australia is Canberra.'
  [6] 'The capital of Australia is Canberra.'
  [7] 'The capital of Australia is Canberra.'
  [8] 'The capital of Australia is Canberra.'
  [9] 'The capital of Australia is Canberra.'

## VRAM
peak VRAM: 5719 MB (5.59 GB) of 15.81 GB
headroom: 10.22 GB

## Verdict
Fits comfortably with headroom for KV cache growth and larger N.
