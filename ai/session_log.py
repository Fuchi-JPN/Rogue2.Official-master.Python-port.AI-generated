"""
session_log.py - JSONL記録・リプレイ読込・差分検知（設計書 §9）
"""
import json
import time
from typing import Optional


class SessionLog:
    def __init__(self, path: str, max_lines: int = 0):
        """path: 記録先。max_lines>0で最新N行のみ保持（ローリング）"""
        self.path = path
        self.max_lines = max_lines
        self._fh = None
        self._count = 0

    def open(self):
        if self.path:
            self._fh = open(self.path, "a", encoding="utf-8")
            if self.max_lines > 0:
                try:
                    with open(self.path, encoding="utf-8") as f:
                        self._count = sum(1 for _ in f)
                except Exception:
                    self._count = 0
                self._trim_locked()

    def write(self, record: dict):
        if self._fh is None:
            return
        try:
            self._fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            self._fh.flush()
            self._count += 1
            if self.max_lines > 0 and self._count > self.max_lines:
                self._trim_locked()
        except Exception:
            pass

    def _trim_locked(self):
        """末尾max_lines行だけ残して切り詰める"""
        try:
            self._fh.flush()
            with open(self.path, encoding="utf-8") as f:
                lines = f.readlines()
            keep = lines[-self.max_lines:]
            with open(self.path, "w", encoding="utf-8") as f:
                f.writelines(keep)
            self._fh.close()
            self._fh = open(self.path, "a", encoding="utf-8")
            self._count = len(keep)
        except Exception:
            pass

    def close(self):
        try:
            if self._fh:
                self._fh.close()
        except Exception:
            pass
        self._fh = None


def load_replay_keys(path: str) -> list:
    """リプレイJSONLから keys 列を取り出す"""
    keys = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            k = rec.get("keys", "")
            if isinstance(k, list):
                keys.extend(k)
            elif isinstance(k, str):
                keys.extend(list(k))
    return keys


def check_anomaly(prev_action: dict, prev_pos, cur_pos, target_passable: bool) -> Optional[str]:
    """移動→不動の想定外を検知する（簡易版）。異常があれば文字列、なければNone"""
    if not prev_action or prev_action.get("type") != "move":
        return None
    if tuple(cur_pos) != tuple(prev_pos) and target_passable:
        return None
    if tuple(cur_pos) == tuple(prev_pos) and target_passable:
        return "blocked unexpectedly: move into passable tile did not change position"
    return None
