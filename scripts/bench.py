#!/usr/bin/env python3
"""Local model benchmark used in the article — standalone, standard library only.

Runs the same tests trend-writer ran against any OpenAI-compatible llama-server:
  speed    fixed-length generation per output type + a long-input prompt (reads timings from llama-server)
  ctx      generation speed at several input lengths (random salt in front, so llama.cpp's prefix cache can't help)
  math     the 10 classic problems, thinking only
  mathtool the same problems with a run_python tool (code runs in `docker run --network none python:3.12`)
  tetris   one-shot single-file HTML Tetris, saved to results/tetris-N.html

Questions, the Tetris feature list and the speed prompts are read from bench/model_bench.md; prompts from prompts/*.md.

  python3 scripts/bench.py --base http://127.0.0.1:10091 --tests speed,ctx,math,mathtool,tetris --out results/rerun.json
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
import time
import urllib.request
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def tables(path: Path) -> dict[str, list[dict]]:
    """Every '## heading' -> its first markdown table as a list of dicts."""
    out, head, header, rows = {}, "", [], []
    for line in path.read_text(encoding="utf-8").splitlines() + ["## end"]:
        if line.startswith("## "):
            if header and rows:
                out.setdefault(head, rows)
            head, header, rows = line[3:].strip(), [], []
        elif line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if not header:
                header = cells
            elif not all(re.fullmatch(r":?-{3,}:?", c) for c in cells):
                rows.append(dict(zip(header, cells)))
    return out


def table(t: dict, key: str) -> list[dict]:
    return next(v for k, v in t.items() if key in k)


def prompt(name: str, **kw) -> tuple[str, str]:
    text = (ROOT / "prompts" / f"{name}.md").read_text(encoding="utf-8")
    m = re.search(r"^## SYSTEM\s*$(.*?)^## USER\s*$(.*)\Z", text, re.S | re.M)
    fill = lambda s: re.sub(r"\{\{\s*(\w+)\s*\}\}", lambda x: str(kw[x.group(1)]), s.strip())   # noqa: E731
    return fill(m.group(1)), fill(m.group(2))


def post(base: str, path: str, body: dict, timeout: float = 2400) -> dict:
    req = urllib.request.Request(base.rstrip("/") + path, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def timings(res: dict) -> dict:
    t = res.get("timings") or {}
    out = {"prompt_n": t.get("prompt_n"), "prompt_tps": round(t.get("prompt_per_second") or 0, 1),
           "gen_n": t.get("predicted_n"), "gen_tps": round(t.get("predicted_per_second") or 0, 1)}
    if t.get("draft_n") is not None:
        out.update(draft_n=t["draft_n"], draft_accepted=t.get("draft_n_accepted"))
    return out


def chat(base: str, messages: list, max_tokens: int, extra: dict | None = None) -> dict:
    return post(base, "/v1/chat/completions", {"messages": messages, "max_tokens": max_tokens, "seed": 42, "cache_prompt": False, **(extra or {})})


def long_text(paragraph: str, tokens: int) -> str:
    n = max(1, tokens // max(1, len(paragraph)))
    return "\n\n".join(f"第 {i + 1} 段：{paragraph}" for i in range(n)) + "\n\n請用五點條列整理上面這份文件的重點。"


ANS = re.compile(r"答案\s*[:：]\s*(.+)")
NUM = re.compile(r"-?\d[\d,]*(?:\.\d+)?(?:\s*/\s*\d+(?:\.\d+)?)?\s*%?")


def to_num(s: str) -> Fraction | None:
    s = re.sub(r"\\d?frac\{([^{}]+)\}\{([^{}]+)\}", r"\1/\2", s or "")
    m = NUM.search(s)
    if not m:
        return None
    raw = m.group(0).replace(",", "").replace(" ", "")
    pct, raw = raw.endswith("%"), raw.rstrip("%")
    try:
        v = Fraction(raw) if "/" not in raw else Fraction(Fraction(raw.split("/")[0]), Fraction(raw.split("/")[1]))
    except (ValueError, ZeroDivisionError):
        return None
    return v / 100 if pct else v


def correct(got: str, answer: str) -> bool:
    g, a = to_num(got), to_num(answer)
    return g is not None and a is not None and abs(float(g) - float(a)) <= 0.005 * max(1.0, abs(float(a)))


def run_python(code: str, seconds: int = 30) -> str:
    """Model-written code runs in a throwaway container without network."""
    with tempfile.TemporaryDirectory() as d:
        Path(d, "run.py").write_text(code, encoding="utf-8")
        try:
            p = subprocess.run(["docker", "run", "--rm", "--network", "none", "--cap-drop", "ALL", "-v", f"{d}:/w:ro", "python:3.12",
                                "timeout", str(seconds), "python3", "/w/run.py"], capture_output=True, text=True, timeout=seconds + 60)
            return (p.stdout + p.stderr)[-4000:] or f"(exit {p.returncode}, no output)"
        except subprocess.TimeoutExpired:
            return "(timeout)"


TOOLS = [{"type": "function", "function": {"name": "run_python", "description": "Run Python 3 code in a sandbox without network and return stdout/stderr (30 s limit). Print the values you need.",
                                           "parameters": {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]}}}]


def math(base: str, problems: list[dict], sampling: dict, tool: bool, max_tokens: int, turns: int) -> list[dict]:
    out = []
    for q in problems:
        system, user = prompt("trial_model_math_tool" if tool else "trial_model_math", question=q["題目"])
        msgs = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        t0, calls, msg, finish, tokens = time.time(), 0, {}, "", 0
        for _ in range(turns if tool else 1):
            res = chat(base, msgs, max_tokens, {**sampling, **({"tools": TOOLS} if tool else {})})
            choice = res["choices"][0]
            msg, finish = choice.get("message") or {}, choice.get("finish_reason") or ""
            tokens += int((res.get("usage") or {}).get("completion_tokens") or 0)
            if not (tool and msg.get("tool_calls")):
                break
            msgs.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": msg["tool_calls"]})
            for c in msg["tool_calls"]:
                calls += 1
                code = json.loads((c.get("function") or {}).get("arguments") or "{}").get("code", "")
                msgs.append({"role": "tool", "tool_call_id": c.get("id", ""), "content": run_python(code)})
        hits = ANS.findall(msg.get("content") or "")
        got = hits[-1].strip() if hits else ""
        out.append({"id": q["編號"], "name": q["名稱"], "answer": q["答案"], "got": got, "correct": correct(got, q["答案"]), "finish": finish,
                    "seconds": round(time.time() - t0, 1), "tokens": tokens, **({"tool_calls": calls} if tool else {})})
        print(f"  {q['編號']} {q['名稱']}: {got or '-'} ({'ok' if out[-1]['correct'] else 'wrong'})", flush=True)
    return out


def extract_html(text: str) -> str:
    blocks = re.findall(r"```(?:html)?\s*\n(.*?)```", text or "", re.S | re.I)
    blocks = [b for b in blocks if "<script" in b.lower() or "<canvas" in b.lower() or "<html" in b.lower()]
    if blocks:
        return max(blocks, key=len).strip()
    m = re.search(r"(?is)(<!doctype html.*?</html>|<html.*?</html>)", text or "")
    return m.group(1).strip() if m else ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="http://127.0.0.1:10091", help="llama-server URL")
    ap.add_argument("--tests", default="speed,ctx,math,mathtool,tetris")
    ap.add_argument("--sampling", default="{}", help='JSON, e.g. {"temperature": 1, "top_p": 1}')
    ap.add_argument("--long-tokens", type=int, default=8000)
    ap.add_argument("--ctx", default="1000,4000,8000,15000")
    ap.add_argument("--math-max-tokens", type=int, default=8192)
    ap.add_argument("--tool-turns", type=int, default=8)
    ap.add_argument("--tetris-runs", type=int, default=3)
    ap.add_argument("--tetris-max-tokens", type=int, default=16384, help="set to the server's context for the bigger-context runs, e.g. 32768")
    ap.add_argument("--effort", default="", help="reasoning effort passed as chat_template_kwargs.reasoning_effort (only if the model's chat template has it), e.g. low")
    ap.add_argument("--out", default=str(ROOT / "results" / "rerun.json"))
    a = ap.parse_args()
    t = tables(ROOT / "bench" / "model_bench.md")
    paragraph = table(t, "長文段落")[0]["段落"]
    sampling = json.loads(a.sampling)
    if a.effort:
        sampling["chat_template_kwargs"] = {**sampling.get("chat_template_kwargs", {}), "reasoning_effort": a.effort}
    want = set(a.tests.split(","))
    res: dict = {"base": a.base, "started": time.strftime("%Y-%m-%dT%H:%M:%S")}
    if "speed" in want:
        res["speed"] = []
        for q in table(t, "速度題"):
            text = long_text(paragraph, a.long_tokens) if q["輸入"] == "長文" else q["輸入"]
            r = chat(a.base, [{"role": "user", "content": text}], int(q["產生 token"]), {"temperature": 0, "ignore_eos": True})
            res["speed"].append({"id": q["編號"], "name": q["名稱"], **timings(r)})
            print(f"speed {q['名稱']}: {res['speed'][-1]}", flush=True)
    if "ctx" in want:
        res["ctx_scan"] = []
        for n in (int(x) for x in a.ctx.split(",")):
            r = chat(a.base, [{"role": "user", "content": f"[{time.time_ns()}]\n" + long_text(paragraph, n)}], 128, {"temperature": 0, "ignore_eos": True})
            res["ctx_scan"].append({"target": n, **timings(r)})
            print(f"ctx {n}: {res['ctx_scan'][-1]}", flush=True)
    problems = table(t, "數學題")
    if "math" in want:
        print("math (thinking only)")
        res["math"] = math(a.base, problems, sampling, False, a.math_max_tokens, 1)
    if "mathtool" in want:
        print("math (with run_python)")
        res["math_tool"] = math(a.base, problems, sampling, True, a.math_max_tokens, a.tool_turns)
    if "tetris" in want:
        checks = "\n".join(f"{i}. {r['功能']}" for i, r in enumerate(table(t, "俄羅斯方塊功能清單"), 1))
        system, user = prompt("trial_model_tetris", checks=checks)
        res["tetris"] = []
        for n in range(1, a.tetris_runs + 1):
            t0 = time.time()
            r = chat(a.base, [{"role": "system", "content": system}, {"role": "user", "content": user}], a.tetris_max_tokens, sampling)
            html = extract_html(r["choices"][0]["message"].get("content") or "")
            if html:
                p = Path(a.out).parent / f"tetris-{n}.html"
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(html, encoding="utf-8")
            res["tetris"].append({"run": n, "seconds": round(time.time() - t0, 1), "chars": len(html), "finish": r["choices"][0].get("finish_reason"),
                                  "tokens": (r.get("usage") or {}).get("completion_tokens")})
            print(f"tetris {n}: {res['tetris'][-1]}", flush=True)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"-> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
