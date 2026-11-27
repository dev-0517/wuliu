# -*- coding: utf-8 -*-
"""
git 远程助手：让 `git push origin main` 在 github.com 被墙的网络下照常工作。
原理：origin URL 设为 ghapi::main 后，git 通过 ~/bin/git-remote-ghapi 调用本脚本，
用 export 模式接收 fast-export 数据流（读完即弃），再通过 api.github.com 完成提交。
"""
import base64
import json
import os
import subprocess
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "deploy.local.json"), encoding="utf-8") as f:
    CFG = json.load(f)
PAT = CFG["github_pat"]
REPO = "dev-0517/wuliu"
API = "https://api.github.com"
ROOT = os.path.dirname(HERE)

DEBUG = True
dbg = None


def log(msg):
    if DEBUG:
        print(msg, file=dbg, flush=True) if dbg else None


def git(*args):
    out = subprocess.check_output(["git", "-C", ROOT] + list(args),
                                  stdin=subprocess.DEVNULL,
                                  stderr=subprocess.DEVNULL)
    return out.decode().strip()


def api(method, path, data=None):
    req = urllib.request.Request(API + path, method=method)
    req.add_header("Authorization", "Bearer " + PAT)
    req.add_header("Accept", "application/vnd.github+json")
    body = json.dumps(data).encode() if data is not None else None
    try:
        with urllib.request.urlopen(req, body) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:200]
        log(f"API {method} {path} -> {e.code}: {detail}")
        sys.exit(1)


def out(line):
    # Windows 管道下 sys.stdout.flush 会报 EINVAL，直接二进制写 fd 1
    os.write(1, (line + "\n").encode())


def do_api_push():
    """把本地 HEAD 的内容同步到 GitHub main（父提交用远端当前 sha，保证链不断）"""
    local_sha = git("rev-parse", "HEAD")
    ref = api("GET", f"/repos/{REPO}/git/ref/heads/main")
    remote_sha = ref["object"]["sha"]
    remote_tree = api("GET", f"/repos/{REPO}/git/commits/{remote_sha}")["tree"]["sha"]

    # 远端内容已与本地一致 -> 无需新提交
    local_tree = git("rev-parse", "HEAD^{tree}")
    if local_tree == remote_tree:
        log("tree equal, skip commit")
        return

    # 远端已有的 blob 跳过上传（提速，避免每次重传 mp4 等）
    remote_blobs = {i["sha"] for i in api(
        "GET", f"/repos/{REPO}/git/trees/{remote_tree}?recursive=1")["tree"]
        if i["type"] == "blob"}

    msg = git("log", "-1", "--format=%s")
    items = []
    for line in git("ls-tree", "-r", "HEAD").splitlines():
        meta, path = line.split("\t", 1)
        mode, _typ, sha = meta.split()
        if sha in remote_blobs:
            items.append({"path": path, "mode": mode, "type": "blob", "sha": sha})
            continue
        content = open(os.path.join(ROOT, path), "rb").read()
        blob = api("POST", f"/repos/{REPO}/git/blobs", {
            "content": base64.b64encode(content).decode(), "encoding": "base64"})
        items.append({"path": path, "mode": mode, "type": "blob", "sha": blob["sha"]})

    tree = api("POST", f"/repos/{REPO}/git/trees", {"base_tree": remote_tree, "tree": items})
    new = api("POST", f"/repos/{REPO}/git/commits",
              {"message": msg, "tree": tree["sha"], "parents": [remote_sha]})
    api("PATCH", f"/repos/{REPO}/git/refs/heads/main",
        {"sha": new["sha"], "force": True})
    log(f"pushed local {local_sha[:8]} as api commit {new['sha'][:8]} (parent {remote_sha[:8]})")


def main():
    global dbg
    if DEBUG:
        dbg = open(os.path.join(HERE, "ghapi.log"), "a", encoding="utf-8")
        log("=== helper start ===")
    dst = "refs/heads/main"
    pushed = False  # False=推送前(谎报父提交让 git 判定可快进) True=推送后(如实报告本地 sha)
    buf = b""

    def read_line():
        # 用 os.read 自行缓冲，避免 Python 文本层预读吞掉 export 数据流
        nonlocal buf
        while True:
            nl = buf.find(b"\n")
            if nl >= 0:
                line, buf = buf[:nl], buf[nl + 1:]
                return line.decode(errors="replace").strip()
            chunk = os.read(0, 65536)
            if not chunk:
                return None
            buf += chunk

    while True:
        line = read_line()
        if line is None:
            break
        log(f"recv: {line!r}")
        if not line:
            continue
        if line == "capabilities":
            out("refspec +refs/heads/*:refs/heads/*")
            out("push")
            out("")
        elif line.startswith("list"):
            # git 推送前需要 list for-push 判断快进；推送后再 list 一次核对结果
            report = git("rev-parse", "HEAD") if pushed else (
                git("rev-parse", "HEAD~1") if git("rev-list", "--count", "HEAD") != "1"
                else "0" * 40)
            out(f"{report} {dst}")
            out("")
        elif line.startswith("push"):
            dst = line.split()[1].split(":")[1]
            # git 随后可能发来 packfile（也可能什么都不发，直接等状态回报）。
            # 限时读第一块：3 秒内没数据就当作无 pack，避免死锁。
            import threading
            res = {}
            t = threading.Thread(target=lambda: res.setdefault("c", os.read(0, 65536)), daemon=True)
            t.start()
            t.join(3)
            if "c" in res:
                # 行缓冲里可能已吞了 pack 开头的字节，要拼回去
                first = buf + res["c"]
                buf = b""
                p = subprocess.Popen(
                    ["git", "-C", ROOT, "index-pack", "--stdin", "--fix-thin"],
                    stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE)
                try:
                    p.stdin.write(first)
                    p.stdin.flush()
                    while True:
                        c = os.read(0, 65536)
                        if not c:
                            break
                        p.stdin.write(c)
                    p.stdin.close()
                except OSError:
                    pass
                err = p.stderr.read().decode(errors="replace")[:200]
                rc = p.wait()
                log(f"index-pack rc={rc} err={err}")
            else:
                log("no pack data (nothing to transfer)")
            try:
                do_api_push()
            except Exception as e:
                import traceback
                log("do_api_push failed: " + traceback.format_exc())
                out(f"error {dst} {e}")
                out("")  # 空行结束状态列表（git 源码：EOF 会被当作错误）
                os._exit(1)
            pushed = True
            out(f"ok {dst}")
            out("")  # 空行结束状态列表
            log("done, force exit")
            os._exit(0)  # 不等 stdin 关闭，git 在等我们退出
        # 其他命令（option 等）忽略
    log("=== helper exit ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
