"""
分两阶段推送：
1. 小文件 (≤500KB) 用 Contents API 上传（小文件多 commit 没关系）
2. 大文件 (PNG) 打包成 tarball 上传为 Release 资产，用户可下载后 re-push
"""
import base64
import json
import os
import sys
import time
import tarfile
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path

REPO = "py7xiaopai/special-web-design"
BRANCH = "main"
TOKEN = os.environ.get("GH_TOKEN") or sys.exit("Set GH_TOKEN env var")
ROOT = Path("/home/jckchen/西游记")
MAX_INLINE = 500 * 1024  # 500KB

SKIP_DIRS = {".git", "__pycache__", ".playwright-mcp"}
SKIP_SUFFIX = (".zimage_done",)


def collect_files():
    out = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        parts = rel.parts
        if any(p in SKIP_DIRS for p in parts):
            continue
        if rel.suffix in SKIP_SUFFIX:
            continue
        out.append(rel)
    return sorted(out)


def api(method, url, body=None, raw_body=None, timeout=60):
    if raw_body is not None:
        data = raw_body
    else:
        data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"token {TOKEN}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if body is not None or raw_body is not None:
        req.add_header("Content-Type", "application/json")
    for attempt in range(3):
        try:
            return urllib.request.urlopen(req, timeout=timeout)
        except urllib.error.HTTPError as e:
            if attempt < 2 and e.code >= 500:
                time.sleep(2 ** attempt)
                continue
            raise


def upload_via_contents(rel, max_retries=3):
    """单个文件用 Contents API 上传"""
    full = ROOT / rel
    raw = full.read_bytes()
    body = {
        "message": f"upload {rel.name}",
        "branch": BRANCH,
        "content": base64.b64encode(raw).decode(),
    }
    url = f"https://api.github.com/repos/{REPO}/contents/{urllib.parse.quote(str(rel))}"

    for attempt in range(max_retries):
        try:
            with api("PUT", url, body) as r:
                return True, r.status
        except urllib.error.HTTPError as e:
            if e.code in (409, 422):
                # 文件已存在
                err = e.read().decode(errors="replace")[:200]
                if "sha" in err or "exists" in err:
                    return True, "exists"
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            return False, f"HTTP {e.code}: {e.read().decode(errors='replace')[:200]}"
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            return False, f"exception: {e}"


def main():
    files = collect_files()
    small = [f for f in files if (ROOT / f).stat().st_size <= MAX_INLINE]
    large = [f for f in files if (ROOT / f).stat().st_size > MAX_INLINE]
    total_size = sum((ROOT / f).stat().st_size for f in files)

    print(f"目标: https://github.com/{REPO} (branch: {BRANCH})")
    print(f"待上传: {len(files)} 个文件 ({total_size//1024//1024} MB)")
    print(f"  小文件 (≤{MAX_INLINE//1024}KB): {len(small)}")
    print(f"  大文件: {len(large)} → 打包成 tarball")
    print()

    # === Phase 1: 小文件 ===
    print(f"=== Phase 1: 上传 {len(small)} 个小文件 ===")
    success, fail = 0, 0
    t0 = time.time()
    for i, rel in enumerate(small, 1):
        size = (ROOT / rel).stat().st_size
        ok, info = upload_via_contents(rel)
        marker = "✓" if ok else "❌"
        print(f"  [{i:>3}/{len(small)}] {marker} {str(rel):60s} ({size:>6d} B) {info if not ok else ''}")
        if ok:
            success += 1
        else:
            fail += 1
    dt = time.time() - t0
    print(f"  → 成功 {success} / 失败 {fail} · 用时 {dt:.0f}s")
    print()

    # === Phase 2: 大文件 tarball + Release ===
    if large:
        print(f"=== Phase 2: {len(large)} 个大文件打包成 tarball ===")
        tar_path = "/tmp/西游记-large-files.tar.gz"
        if os.path.exists(tar_path):
            os.remove(tar_path)
        with tarfile.open(tar_path, "w:gz") as tar:
            for rel in large:
                tar.add(ROOT / rel, arcname=str(rel))
        tar_size = os.path.getsize(tar_path)
        print(f"  tarball: {tar_path} ({tar_size//1024//1024} MB)")

        # 删旧 release
        try:
            with api("GET", f"https://api.github.com/repos/{REPO}/releases/tags/large-files") as r:
                old = json.loads(r.read())
                with api("DELETE", f"https://api.github.com/repos/{REPO}/releases/{old['id']}") as r2:
                    print(f"  已删除旧 release")
        except urllib.error.HTTPError:
            pass

        # 创建 release
        print(f"  创建 release 'large-files'...")
        with api("POST", f"https://api.github.com/repos/{REPO}/releases", {
            "tag_name": "large-files",
            "name": "Large binary assets (illustrations)",
            "body": "Tarball of PNG illustrations. Download, extract, and `git add` to add to the repo.",
            "draft": False,
            "prerelease": True,
        }) as r:
            release = json.loads(r.read())
        upload_url = release["upload_url"].split("{")[0]
        print(f"  release URL: {release['html_url']}")

        # 上传 tarball
        print(f"  上传 tarball（{tar_size//1024//1024} MB）...")
        with open(tar_path, "rb") as f:
            tar_data = f.read()
        url = f"{upload_url}?name={urllib.parse.quote('large-files.tar.gz')}"
        req = urllib.request.Request(url, data=tar_data, method="POST")
        req.add_header("Authorization", f"token {TOKEN}")
        req.add_header("Content-Type", "application/gzip")
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                asset = json.loads(r.read())
            print(f"  ✓ 资产上传: {asset['browser_download_url']}")
        except Exception as e:
            print(f"  ❌ 上传失败: {e}")
            return

    print(f"\n✅ 推送完成。Pages 地址: https://py7xiaopai.github.io/special-web-design/")


if __name__ == "__main__":
    main()
