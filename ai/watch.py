"""
watch.py - 60秒ごとのログ監視・異常検知ループ（追補28）

ai_session.jsonl / ai_trace.jsonl / rogue_debug.log を増分追跡し、
異常パターンを検知して ai_anomalies.jsonl に記録する。
修正の自動適用は行わない（検知＋報告＋任意フックまで）。
自動修正したい場合は --on-anomaly でエージェントCLI等を呼び出す。

使い方:
  python3 watch.py                      # 60秒間隔で継続監視
  python3 watch.py --interval 30        # 間隔変更
  python3 watch.py --once               # 1回だけ検査
  python3 watch.py --on-anomaly 'echo {report}'   # 検知時フック
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

SESSION = "ai_session.jsonl"
TRACE = "ai_trace.jsonl"
DEBUGLOG = "rogue_debug.log"
REPORT = "ai_anomalies.jsonl"
STATE = "ai_watch.state.json"

# 連続系の閾値
THRASH_N = 8        # 同一行動の連続（位置不変）
CORRECT_N = 5       # 補正の連続（壁手/攻撃/通路/探索）
STUCK_RE = re.compile(r"stuck|no progress|停滞", re.I)
MISS_MSGS = ("そこには何もいない", "そのコマンドは不明です")


def _load_jsonl_tail(path, offset):
    """offsetバイト以降のJSON行を返す。(records, new_offset)"""
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            f.seek(offset)
            lines = f.read().splitlines()
            new_offset = f.tell()
    except FileNotFoundError:
        return [], offset
    except Exception:
        return [], offset
    recs = []
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        try:
            recs.append(json.loads(ln))
        except ValueError:
            recs.append({"_raw": ln[:200]})
    return recs, new_offset


def _load_text_tail(path, offset):
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            f.seek(offset)
            data = f.read()
            new_offset = f.tell()
    except FileNotFoundError:
        return "", offset
    except Exception:
        return "", offset
    return data, new_offset


def detect(session_recs, trace_recs, debug_text):
    """異常リストを返す。各要素は dict(kind, severity, detail)。"""
    out = []

    # 1. クラッシュ・例外（debug log）
    for pat, kind in ((r"Traceback", "crash"),
                      (r"ゲームエラー", "crash"),
                      (r"AttributeError|TypeError|KeyError|IndexError", "exception")):
        m = re.search(pat, debug_text)
        if m:
            # 直近の該当行を抜粋
            lines = [ln for ln in debug_text.splitlines() if re.search(pat, ln)]
            out.append({"kind": kind, "severity": "fatal",
                        "detail": "; ".join(lines[-3:])[:300]})
            break

    # 2. 停止・死亡
    for r in session_recs:
        if isinstance(r, dict) and r.get("event", "").startswith("stop:"):
            out.append({"kind": "stop", "severity": "info",
                        "detail": "%s (turn %s)" % (r["event"], r.get("turn"))})
        obs = r.get("obs") if isinstance(r, dict) else None
        if isinstance(obs, dict) and isinstance(obs.get("hp"), list):
            hp = obs["hp"]
            if hp and hp[0] <= 0:
                out.append({"kind": "death", "severity": "high",
                            "detail": "HP 0 at turn %s pos %s" % (r.get("turn"), obs.get("pos"))})
                break

    # 3. 同一行動の空転（位置不変の連続）
    seq = [(json.dumps((r.get("action") or {}), sort_keys=True),
            tuple((r.get("obs") or {}).get("pos") or ())) for r in session_recs
           if isinstance(r, dict) and r.get("action")]
    if len(seq) >= THRASH_N:
        tail = seq[-THRASH_N:]
        if len({a for a, _ in tail}) == 1 and len({p for _, p in tail}) == 1:
            out.append({"kind": "thrash", "severity": "high",
                        "detail": "same action %s x%d at %s" % (tail[0][0][:80], THRASH_N, tail[0][1])})

    # 4. 補正の連続（壁手/攻撃/通路/探索）
    corr = [str(r.get("thought", "")) for r in session_recs if isinstance(r, dict)]
    for kw, name in (("壁手補正", "wall-correction"), ("攻撃修正", "fight-correction"),
                     ("通路追従", "corridor-correction"), ("隠し扉探索", "deadend-search")):
        run = 0
        for t in corr[-12:]:
            run = run + 1 if kw in t else 0
        if run >= CORRECT_N:
            out.append({"kind": name, "severity": "medium",
                        "detail": "%s x%d consecutive" % (kw, run)})
            break

    # 5. 戦闘空振り・不明コマンドの反復
    miss = 0
    for r in session_recs[-12:]:
        if not isinstance(r, dict):
            continue
        obs = r.get("obs") or {}
        msg = str(obs.get("message") or "")
        miss = miss + 1 if any(m in msg for m in MISS_MSGS) else 0
    if miss >= 3:
        out.append({"kind": "miss-repeat", "severity": "medium",
                    "detail": "miss message x%d" % miss})

    # 6. LLM失敗・停止
    for r in session_recs:
        if isinstance(r, dict) and r.get("event", "").startswith("LLM"):
            out.append({"kind": "llm-error", "severity": "high",
                        "detail": r["event"][:200]})

    # 7. stuck停止
    for r in session_recs:
        if isinstance(r, dict) and STUCK_RE.search(str(r.get("event", ""))):
            out.append({"kind": "stuck", "severity": "high",
                        "detail": "%s (turn %s)" % (r["event"], r.get("turn"))})

    return out


def load_state(log_dir):
    p = os.path.join(log_dir, STATE)
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(log_dir, state):
    try:
        with open(os.path.join(log_dir, STATE), "w", encoding="utf-8") as f:
            json.dump(state, f)
    except Exception:
        pass


def check_once(log_dir):
    state = load_state(log_dir)
    results = []
    for key, path, loader in (("session", SESSION, _load_jsonl_tail),
                              ("trace", TRACE, _load_jsonl_tail),
                              ("debug", DEBUGLOG, _load_text_tail)):
        full = os.path.join(log_dir, path)
        off = state.get(key, 0)
        try:
            if os.path.getsize(full) < off:
                off = 0  # ローテーション等で縮んだら先頭から
        except OSError:
            pass
        data, new_off = loader(full, off)
        state[key] = new_off
        results.append(data)
    save_state(log_dir, state)
    anomalies = detect(results[0], results[1], results[2])
    if anomalies:
        rep_path = os.path.join(log_dir, REPORT)
        try:
            with open(rep_path, "a", encoding="utf-8") as f:
                for a in anomalies:
                    a = dict(a)
                    a["time"] = time.strftime("%Y-%m-%dT%H:%M:%S")
                    f.write(json.dumps(a, ensure_ascii=False) + "\n")
        except Exception:
            pass
    return anomalies


def main(argv=None):
    ap = argparse.ArgumentParser(description="AIプレイのログ監視ループ")
    ap.add_argument("--interval", type=int, default=60)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--log-dir", default=".")
    ap.add_argument("--on-anomaly", default="")
    ns = ap.parse_args(argv)
    while True:
        anomalies = check_once(ns.log_dir)
        for a in anomalies:
            line = "[%s] %s: %s" % (a["severity"], a["kind"], a["detail"])
            print(line, flush=True)
            if ns.on_anomaly:
                try:
                    subprocess.run(ns.on_anomaly.replace("{report}", json.dumps(a, ensure_ascii=False)),
                                   shell=True, timeout=300)
                except Exception as e:
                    print("hook failed: %s" % e, flush=True)
        if ns.once:
            break
        time.sleep(max(1, ns.interval))


if __name__ == "__main__":
    main()
