"""KataGo analysis 引擎进程封装：启动、发请求、收结果。"""

import json
import queue
import subprocess
import threading


class KataGoEngine:
    def __init__(self, katago_path, model_path, config_path=None, on_log=None):
        self.katago_path = katago_path
        self.model_path = model_path
        self.config_path = config_path
        self.on_log = on_log
        self.proc = None
        self._writer = None
        self._lock = threading.Lock()
        self._cond = threading.Condition()
        self._pending = {}
        self._results = {}
        self._next_id = 0
        self._reader_thread = None
        self._stderr_thread = None

    # ---------- 生命周期 ----------
    def start(self):
        cmd = [self.katago_path, "analysis", "-model", self.model_path]
        if self.config_path:
            cmd += ["-config", self.config_path]
        self.proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1, encoding="utf-8", errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        self._writer = self.proc.stdin
        self._reader_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._reader_thread.start()
        self._stderr_thread = threading.Thread(target=self._read_stderr, daemon=True)
        self._stderr_thread.start()

    def is_running(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def stop(self):
        if self.proc is not None and self.proc.poll() is None:
            try:
                self.proc.terminate()
            except Exception:
                pass
            try:
                self.proc.kill()
            except Exception:
                pass
        self.proc = None

    def warmup(self):
        """用空棋盘低 visits 触发 GPU 编译/加载，让正式分析更快。"""
        self.analyze(moves=[], board_size=19, komi=7.5, max_visits=8, timeout=120)

    # ---------- 请求 ----------
    def analyze(self, moves, board_size=19, komi=7.5, rules="chinese",
                max_visits=600, include_ownership=False, timeout=30.0):
        if not self.is_running():
            raise RuntimeError("KataGo 引擎未运行")
        with self._lock:
            self._next_id += 1
            qid = f"q{self._next_id}"
        payload = {
            "id": qid,
            "moves": moves,
            "rules": rules,
            "komi": komi,
            "boardXSize": board_size,
            "boardYSize": board_size,
            "maxVisits": max_visits,
            "includeOwnership": include_ownership,
            "includePolicy": True,
        }
        with self._cond:
            self._pending[qid] = True
            self._results[qid] = None
        self._writer.write(json.dumps(payload) + "\n")
        self._writer.flush()
        with self._cond:
            self._cond.wait_for(
                lambda: self._results.get(qid) is not None
                        and not self._results[qid].get("isDuringSearch", True),
                timeout=timeout,
            )
        with self._cond:
            self._pending.pop(qid, None)
            result = self._results.pop(qid, None)
        if result is None:
            raise TimeoutError(f"KataGo 分析超时（{timeout}s）")
        return result

    # ---------- 内部 ----------
    def _read_loop(self):
        for line in self.proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            qid = obj.get("id")
            with self._cond:
                if qid in self._pending:
                    self._results[qid] = obj
                    if not obj.get("isDuringSearch", True):
                        self._cond.notify_all()

    def _read_stderr(self):
        for line in self.proc.stderr:
            line = line.rstrip()
            if line and self.on_log:
                try:
                    self.on_log(line)
                except Exception:
                    pass
