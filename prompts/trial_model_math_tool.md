# 本地模型實測：數學題，給 Python 工具（送給被測的本地模型，stages/trial/model.py _ask_math）

同一批數學題再跑一次，這次模型可以呼叫 run_python（沒有網路的容器，每次 30 秒）。程式從回答最後的「答案：」那行對答案。
變數：question。

## SYSTEM

你可以呼叫 run_python 工具執行 Python 程式來計算或驗算（要看結果就 print）。算完在最後一行只寫「答案：」加上最後的數字（分數寫成 a/b，不要單位）。

## USER

{{question}}
