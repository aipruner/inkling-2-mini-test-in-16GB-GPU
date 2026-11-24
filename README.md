# Inkling-2-Mini local test (NVIDIA GeForce RTX 4060 Ti, 16GB)

Code, prompts and raw results from testing **thinkingmachines/Inkling-2-Mini** on one NVIDIA GeForce RTX 4060 Ti with llama.cpp in Docker (2026-11-24).

> NVIDIA GeForce RTX 4060 Ti 16GB 跑 UD-Q3_K_XL：最快的設定是「DSpark draft 3」，產生 55.8 tok/s、顯存峰值 15.0 GB。經典數學 10 題：UD-Q3_K_XL 9/10、UD-IQ3_XXS 10/10、UD-IQ4_XS 9/10、UD-Q3_K_XL＋Python 工具 10/10。俄羅斯方塊（UD-Q3_K_XL）原本設定（context 16384）3 次寫出 1 次；context 放大到 32K（KV cache q8_0） 3/3 次；推理強度調成 low 3/3 次（功能清單逐條核對的結果見下表）。

## Setup under test

| | |
|---|---|
| Model | [`thinkingmachines/Inkling-2-Mini`](https://huggingface.co/thinkingmachines/Inkling-2-Mini) |
| Quant files | [`unsloth/Inkling-2-Mini-GGUF`](https://huggingface.co/unsloth/Inkling-2-Mini-GGUF) — main `UD-Q3_K_XL` |
| Engine | llama.cpp `https://github.com/unslothai/llama.cpp` b12651-mix-c7059d6 (image `tw-llama-unslothai-llama.cpp:b12651-mix-c7059d6`) |
| GPU | NVIDIA GeForce RTX 4060 Ti, 16.0 GB VRAM, driver 580.178.04 |
| RAM / CPU | 62.7 GB / 12 threads |
| Fastest config | `-c 16384 -np 1 -ngl 99 -md ./models/unsloth/Inkling-2-Mini-GGUF/dspark-Inkling-2-Mini-Q8_0.gguf --spec-type draft-dspark --spec-draft-n-max 3 -ngld 99` |
| Sampling (math, Tetris) | `{"temperature": 1.0, "top_p": 1.0, "top_k": 0, "min_p": 0.0}` |
| Question set | `bench/model_bench.md` v2 |

Full run: 91 requests, 250809 tokens, 3746.0 s, GPU energy ≈ 0.111 kWh (GPU only). Then only `tetris` was rerun:

Rerun: 12 requests, 190861 tokens, 3562.3 s, GPU energy ≈ 0.118 kWh (GPU only).

## Which quant fits

| Quant | Size | On this card |
|---|---:|---|
| UD-IQ1_S | 7.76 GB | fully on GPU |
| UD-IQ1_M | 8.02 GB | fully on GPU |
| UD-IQ2_XXS | 8.49 GB | fully on GPU |
| UD-Q2_K_XL | 9.14 GB | fully on GPU |
| UD-IQ3_XXS | 11.66 GB | fully on GPU |
| UD-Q3_K_XL | 13.63 GB | fully on GPU |
| UD-IQ4_XS | 15.73 GB | needs MoE experts on CPU |
| UD-Q4_K_M | 16.61 GB | needs MoE experts on CPU |
| UD-Q4_K_XL | 17.63 GB | needs MoE experts on CPU |
| UD-Q8_K_XL | 22.87 GB | needs MoE experts on CPU |

## Configs (speed and memory)

| Config | Group | Quant | Status | VRAM peak | Gen tok/s | Prompt tok/s | Draft accept |
|---|---|---|---|---:|---:|---:|---:|
| 基準 | baseline | UD-Q3_K_XL | ok | 13.8 GB | 52.3 | 1054.7 | — |
| 關閉 Flash Attention | Flash Attention | UD-Q3_K_XL | oom | — | — | — | — |
| KV cache Q8 量化 | KV cache quant | UD-Q3_K_XL | ok | 13.4 GB | 51.8 | 1040.0 | — |
| DSpark draft 2 | speculative decoding | UD-Q3_K_XL | ok | 15.1 GB | 54.8 | 1042.3 | 52% |
| DSpark draft 3 **(fastest)** | speculative decoding | UD-Q3_K_XL | ok | 15.1 GB | 55.8 | 1041.3 | 42% |
| IQ3 量化 | other quant | UD-IQ3_XXS | ok | 12.0 GB | 55.1 | 1036.1 | — |
| IQ4 MoE 放 CPU | MoE experts on CPU | UD-IQ4_XS | ok | 9.3 GB | 22.0 | 278.7 | — |

Generation speed by output type (fastest config): 短問答 52.0, 寫程式 65.1, 英文散文 49.5, HTML 程式 56.5 tok/s.

## Context length scan

| Input tokens | Prompt tok/s | Gen tok/s |
|---:|---:|---:|
| 720 | 894.5 | 50.3 |
| 3432 | 1070.4 | 54.5 |
| 6822 | 1043.6 | 54.8 |
| 12924 | 1019.8 | 52.1 |

## Math (10 classic problems, answers checked by code)

| Problem | Answer | UD-Q3_K_XL | UD-IQ3_XXS | UD-IQ4_XS | UD-Q3_K_XL + Python tool |
|---|---|---|---|---|---|
| 雞兔同籠 | 12 | ✓ 10.0s | ✓ 6.9s | ✓ 24.0s | ✓ 13.2s |
| 鐘面夾角 | 7.5 | ✓ 10.8s | ✓ 12.3s | ✓ 50.1s | ✓ 15.5s |
| 河內塔 | 127 | ✓ 31.3s | ✓ 20.6s | ✓ 37.0s | ✓ 15.8s |
| 階乘尾數 | 24 | ✓ 10.7s | ✓ 10.7s | ✓ 41.3s | ✓ 12.5s |
| 蒙提霍爾 | 2/3 | ✓ 23.5s | ✓ 34.0s | ✓ 80.3s | ✓ 20.1s |
| 生日問題 | 23 | ✓ 63.6s | ✓ 34.5s | ✓ 74.8s | ✓ 18.5s |
| 韓信點兵 | 23 | ✓ 18.1s | ✓ 12.0s | ✓ 28.4s | ✓ 14.6s |
| 排容原理 | 266 | ✓ 15.5s | ✓ 16.6s | ✓ 45.3s | ✓ 17.4s |
| 猴子分桃 | 3121 | ✗ no stop 139.8s | ✓ 82.5s | ✗ no stop 392.8s | ✓ 156.5s |
| 水池問題 | 3 | ✓ 11.4s | ✓ 12.4s | ✓ 36.0s | ✓ 19.7s |
| **Total** | | **9/10** · 334.7s | **10/10** · 242.5s | **9/10** · 810.0s | **10/10** · 303.8s |

## Tetris (one shot, one fix round if the page throws errors)

Runs that ran out of context with the default setup (context 16384, model-default reasoning effort) were followed by extra runs with other setups: context 32768 + KV cache q8_0 (-ctk/-ctv); reasoning_effort=low (chat_template_kwargs).

| Run | Setup | Result | Time | Tokens | Feature checks |
|---|---|---|---:|---:|---:|
| 1 | context 16384 | opens, fixed once | 512.6s | 31982 | 10/10 |
| 2 | context 16384 | no HTML, retried once | 565.6s | 32287 | — |
| 3 | context 16384 | no HTML, retried once | 555.7s | 32287 | — |
| 4 | context 32768 + KV cache q8_0 (-ctk/-ctv) | opens | 595.5s | 30369 | 10/10 |
| 5 | context 32768 + KV cache q8_0 (-ctk/-ctv) | opens | 544.3s | 29492 | 10/10 |
| 6 | context 32768 + KV cache q8_0 (-ctk/-ctv) | opens | 303.6s | 16326 | 10/10 |
| 7 | context 16384 + reasoning_effort=low (chat_template_kwargs) | opens | 66.5s | 4741 | 10/10 |
| 8 | context 16384 + reasoning_effort=low (chat_template_kwargs) | opens | 76.2s | 5455 | 8/10 |
| 9 | context 16384 + reasoning_effort=low (chat_template_kwargs) | opens | 67.4s | 4571 | 10/10 |

Generated files: `results/tetris-N.html`; screenshots in `images/`.

## Rerun

1. Download the GGUF files listed in `scripts/run_server.sh` into `./models/`.
2. Start the server (same flags as the fastest config):

```bash
bash scripts/run_server.sh
```

3. Run the same tests (needs Docker for the Python tool sandbox):

```bash
python3 scripts/bench.py --base http://127.0.0.1:10091 --sampling '{"temperature": 1.0, "top_p": 1.0, "top_k": 0, "min_p": 0.0}'
```

Extra Tetris runs with context 32768 + KV cache q8_0 (-ctk/-ctv): start the server with `-c 32768 -ctk q8_0 -ctv q8_0` added (replacing `-c`), then `python3 scripts/bench.py --tests tetris --tetris-max-tokens 32768 --sampling '{"temperature": 1.0, "top_p": 1.0, "top_k": 0, "min_p": 0.0}'`

Extra Tetris runs with reasoning_effort=low (chat_template_kwargs): same server, then `python3 scripts/bench.py --tests tetris --effort low --sampling '{"temperature": 1.0, "top_p": 1.0, "top_k": 0, "min_p": 0.0}'`

## Layout

```
bench/model_bench.md   questions, Tetris feature list, speed prompts (question set v2)
prompts/               prompts sent to the model
scripts/bench.py       standalone benchmark (standard library only)
scripts/run_server.sh  download + llama-server commands that were actually run
results/               model.json, plan.json, per-step logs, Tetris HTML
images/                tables and screenshots used in the article
```

All numbers come from one machine and one run per test. Classic math problems may be in the training data.

<details><summary>Exact server command</summary>

```bash
docker run -d --name tw-model-20261124-article-c5 --gpus all --user 1003:1004 --cap-drop ALL --security-opt no-new-privileges --memory 48g --pids-limit 2048 -p 127.0.0.1:10091:8080 -v ./models:/models:ro tw-llama-unslothai-llama.cpp:b12651-mix-c7059d6 -m /models/unsloth/Inkling-2-Mini-GGUF/Inkling-2-Mini-UD-Q3_K_XL.gguf --host 0.0.0.0 --port 8080 -c 16384 -np 1 -ngl 99 -md /models/unsloth/Inkling-2-Mini-GGUF/dspark-Inkling-2-Mini-Q8_0.gguf --spec-type draft-dspark --spec-draft-n-max 3 -ngld 99
```
</details>
