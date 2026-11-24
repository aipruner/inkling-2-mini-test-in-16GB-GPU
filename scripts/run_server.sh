#!/usr/bin/env bash
# Commands that were actually run (paths rewritten to ./models). Fastest config: DSpark draft 3
set -euo pipefail
mkdir -p models

# download
curl -L --fail -sS -C - -o ./models/unsloth/Inkling-2-Mini-GGUF/Inkling-2-Mini-UD-Q3_K_XL.gguf https://huggingface.co/unsloth/Inkling-2-Mini-GGUF/resolve/main/Inkling-2-Mini-UD-Q3_K_XL.gguf
curl -L --fail -sS -C - -o ./models/unsloth/Inkling-2-Mini-GGUF/dspark-Inkling-2-Mini-Q8_0.gguf https://huggingface.co/unsloth/Inkling-2-Mini-GGUF/resolve/main/dspark-Inkling-2-Mini-Q8_0.gguf
curl -L --fail -sS -C - -o ./models/unsloth/Inkling-2-Mini-GGUF/Inkling-2-Mini-UD-IQ3_XXS.gguf https://huggingface.co/unsloth/Inkling-2-Mini-GGUF/resolve/main/Inkling-2-Mini-UD-IQ3_XXS.gguf
curl -L --fail -sS -C - -o ./models/unsloth/Inkling-2-Mini-GGUF/Inkling-2-Mini-UD-IQ4_XS.gguf https://huggingface.co/unsloth/Inkling-2-Mini-GGUF/resolve/main/Inkling-2-Mini-UD-IQ4_XS.gguf

# server
docker run -d --name tw-model-20261124-article-c5 --gpus all --user 1003:1004 --cap-drop ALL --security-opt no-new-privileges --memory 48g --pids-limit 2048 -p 127.0.0.1:10091:8080 -v $PWD/models:/models:ro tw-llama-unslothai-llama.cpp:b12651-mix-c7059d6 -m /models/unsloth/Inkling-2-Mini-GGUF/Inkling-2-Mini-UD-Q3_K_XL.gguf --host 0.0.0.0 --port 8080 -c 16384 -np 1 -ngl 99 -md /models/unsloth/Inkling-2-Mini-GGUF/dspark-Inkling-2-Mini-Q8_0.gguf --spec-type draft-dspark --spec-draft-n-max 3 -ngld 99
