# -*- coding: utf-8 -*-
"""
一键部署脚本（在 VS Code 终端运行）：
    python scripts/deploy.py "提交说明"

自动完成：
  1. 通过 GitHub API 把本地最新提交推到 main（github.com 直连被墙，走 api.github.com）
  2. 轮询等待 GitHub Actions 构建镜像并推到阿里云 ACR
  3. SSH 到 ECS 执行 pull-deploy.sh 拉取新镜像重建容器
"""
import base64
import json
import os
import sys
import time
import urllib.request

import paramiko

# ---------- 配置：密钥从 scripts/deploy.local.json（已 gitignore，不入仓库）读取 ----------
HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "deploy.local.json"), encoding="utf-8") as f:
    CFG = json.load(f)

PAT = CFG["github_pat"]
REPO = "dev-0517/wuliu"
BRANCH = "main"
API = "https://api.github.com"

ECS_HOST = CFG["ecs_host"]
ECS_USER = CFG["ecs_user"]
ECS_PASS = CFG["ecs_pass"]
DEPLOY_CMD = "bash /opt/wuliu/scripts/pull-deploy.sh && tail -1 /tmp/wuliu-pull-check.log"

# 本地要保证已提交：脚本直接读取 HEAD 的 tree 与远程比对
ROOT = os.path.dirname(HERE)


def api(method, path, data=None):
    req = urllib.request.Request(API + path, method=method)
    req.add_header("Authorization", "Bearer " + PAT)
    req.add_header("Accept", "application/vnd.github+json")
    body = json.dumps(data).encode() if data is not None else None
    try:
        with urllib.request.urlopen(req, body) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        print(f"    API {method} {path} -> {e.code}: {e.read().decode(errors='replace')[:300]}")
        raise


def local_git(*args):
    import subprocess
    out = subprocess.check_output(["git", "-C", ROOT] + list(args))
    return out.decode().strip()


def main():
    msg = sys.argv[1] if len(sys.argv) > 1 else "update"
    dirty = local_git("status", "--porcelain")
    if dirty:
        print("[0/4] 本地有未提交改动，自动提交...")
        local_git("add", "-A")
        local_git("commit", "-m", msg)
    else:
        print("[0/4] 工作区干净，直接推送当前提交")

    # 1. 远程 main 当前状态
    ref = api("GET", f"/repos/{REPO}/git/ref/heads/{BRANCH}")
    remote_sha = ref["object"]["sha"]
    remote = api("GET", f"/repos/{REPO}/git/commits/{remote_sha}")
    remote_tree = remote["tree"]["sha"]

    # 2. 本地 HEAD 内容全部上传为 blob
    local_sha = local_git("rev-parse", "HEAD")
    msg = local_git("log", "-1", "--format=%s")  # 用本地提交说明
    print(f"[1/4] 推送本地提交 {local_sha[:8]}: {msg}")
    tree_items = []
    for line in local_git("ls-tree", "-r", "HEAD").splitlines():
        meta, path = line.split("\t", 1)
        mode, typ, sha = meta.split()
        if typ != "blob":
            continue
        # 与远程 tree 中相同 sha 的文件跳过上传
        tree_items.append({"path": path, "mode": mode, "type": "blob", "sha": sha})
        content = open(f"{ROOT}/{path}", "rb").read()
        print(f"    blob {path} ({len(content)} bytes)")
        blob = api("POST", f"/repos/{REPO}/git/blobs", {
            "content": base64.b64encode(content).decode(), "encoding": "base64"})
        tree_items[-1]["sha"] = blob["sha"]

    tree = api("POST", f"/repos/{REPO}/git/trees", {"base_tree": remote_tree, "tree": tree_items})
    commit = api("POST", f"/repos/{REPO}/git/commits",
                 {"message": msg, "tree": tree["sha"], "parents": [remote_sha]})
    if commit["sha"] == remote_sha:
        print("    远程已是最新，跳过推送")
        new_sha = remote_sha
    else:
        api("PATCH", f"/repos/{REPO}/git/refs/heads/{BRANCH}", {"sha": commit["sha"]})
        new_sha = commit["sha"]
        print(f"    推送成功 -> {new_sha[:8]}")

    # 3. 等 Actions 构建完成
    print("[2/4] 等待 GitHub Actions 构建镜像...")
    for i in range(60):
        time.sleep(15)
        runs = api("GET", f"/repos/{REPO}/actions/runs?head_sha={new_sha}&per_page=1")
        if not runs["workflow_runs"]:
            if i > 4:
                print("    还没看到对应的构建记录...")
            continue
        r = runs["workflow_runs"][0]
        print(f"    [{i*15}s] status={r['status']} conclusion={r['conclusion']}")
        if r["status"] == "completed":
            if r["conclusion"] != "success":
                print("    构建失败！登录 GitHub 查看日志：https://github.com/dev-0517/wuliu/actions")
                sys.exit(1)
            break
    else:
        print("    等待超时（15 分钟），请稍后手动重试本脚本")
        sys.exit(1)

    # 4. SSH 到 ECS 拉取部署
    print("[3/4] 服务器拉取新镜像部署...")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(ECS_HOST, username=ECS_USER, password=ECS_PASS, timeout=15)
    _, o, _ = c.exec_command(DEPLOY_CMD, timeout=300)
    out = o.read().decode(errors="replace").strip()
    c.close()
    print("    " + (out.replace("\n", "\n    ") or "(无输出)"))

    print("[4/4] 部署完成！访问 http://120.55.102.191 检查效果")


if __name__ == "__main__":
    main()
