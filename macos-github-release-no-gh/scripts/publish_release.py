#!/usr/bin/env python3
"""Idempotent GitHub release publisher (no `gh` CLI needed).

Reads token from env var TOKEN. Creates the repo if missing, pushes is NOT
done here (use git separately), creates a release (checks-then-creates),
and uploads assets (checks-then-uploads). Uses only stdlib so JSON with
newlines never hits shell escaping bugs.

2026-11-05 修复两个实测踩到的坑：
  1. 资产文件名未做 URL 编码 —— 中文/空格文件名直接抛
     UnicodeEncodeError: 'ascii' codec can't encode characters。
     现在统一 urllib.parse.quote(name, safe="")。
  2. 大文件（>50MB）POST 在内网透明代理下必被 broken pipe 截断
     （实测在 16–59MB 之间随机断）。现在：
       · 上传显式 Content-Length、走 HTTP/1.1，避免 chunked/HTTP2 长 POST
       · 文件 > LARGE_MB 时自动限速（900KB/s 起），防止代理缓冲区溢出
       · 失败自动重试 3 次，速率阶梯 900k → 600k → 400k
       · 上传后比对服务器返回 size，不一致视为失败
  3. **GitHub Release 资产名不支持非 ASCII**（2026-11-05 实测）：
     `12-数码兽全属性图鉴-1.4.15-universal.dmg` 会被服务器**静默剥离**成
     `12-.-1.4.15-universal.dmg`，`测试 中文 文件名.txt` 直接变 `default.txt`。
     现在上传前自动做 ASCII 安全化并打印改名提示；上传后再校验服务器
     返回的 name 是否与请求一致，不一致即判失败。
"""
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
import urllib.parse
import argparse

API = "https://api.github.com"
UPLOAD = "https://uploads.github.com"

LARGE_MB = 50
DEFAULT_LARGE_RATE = 900 * 1024
RATE_LADDER = [900 * 1024, 600 * 1024, 400 * 1024]
CHUNK = 64 * 1024
RETRIES = 3


def ascii_asset_name(name):
    """GitHub Release 资产名不支持非 ASCII，服务器会静默剥离中文字符。

    实测（2026-11-05）：
      '12-数码兽全属性图鉴-1.4.15-universal.dmg' → '12-.-1.4.15-universal.dmg'
      '测试 中文 文件名.txt'                     → 'default.txt'

    这里提前做 ASCII 安全化，避免传到一半才发现名字被改。
    返回 (safe_name, changed)。
    """
    if all(ord(c) < 128 for c in name):
        return name, False

    stem, ext = os.path.splitext(name)
    # 非 ASCII 先变空格，再压缩连续分隔符
    s = ''.join(c if ord(c) < 128 else ' ' for c in stem)
    s = re.sub(r'[\\/:*?"<>|]+', ' ', s)      # 服务器不接受的字符
    s = re.sub(r'[\s\-_]{2,}', '-', s)
    s = s.strip(' -_.')
    if not s:
        s = 'asset'
    if not all(ord(c) < 128 for c in ext):
        ext = ''
    return s + ext, True


class RateLimitedFile:
    """把本地文件包装成可限速的 file-like，供 urllib 流式读取请求体。

    为什么要限速：本机走内网透明代理时，>50MB 的 POST 会在 16–59MB
    处被代理掐断（broken pipe）。限速让发送速率低于代理缓冲区消化能力，
    即可稳定传完（实测 214MB @900KB/s 用时 237s，HTTP 201）。
    """

    def __init__(self, path, rate_bps=0):
        self.path = path
        self.f = open(path, "rb")
        self.size = os.path.getsize(path)
        self.rate = max(0, int(rate_bps or 0))
        self.sent = 0
        self.t0 = time.monotonic()

    def read(self, n=-1):
        want = CHUNK if (n is None or n < 0) else min(n, CHUNK)
        data = self.f.read(want)
        if data and self.rate:
            self.sent += len(data)
            target = self.sent / self.rate          # 应耗时
            elapsed = time.monotonic() - self.t0
            if elapsed < target:
                time.sleep(target - elapsed)
        return data

    def close(self):
        try:
            self.f.close()
        except Exception:
            pass


def api(token, method, url, data=None, binary=False, timeout=1800):
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "publish-release-script",
    }
    body = None
    if data is not None:
        if binary:
            headers["Content-Type"] = "application/octet-stream"
            body = data
        else:
            headers["Content-Type"] = "application/json"
            body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode()
    except urllib.error.HTTPError as e:
        return e.read().decode()
    except Exception as e:
        return json.dumps({"message": f"transport error: {e}"})


def ensure_repo(token, owner, name, description, private=False):
    r = api(token, "GET", f"{API}/repos/{owner}/{name}")
    if r and '"id"' in r:
        d = json.loads(r)
        print(f"repo {owner}/{name} 已存在 (private={d.get('private')})")
        # 请求私有但实际是公开 —— 纠正可见性，避免源码外泄
        if private and not d.get("private"):
            api(token, "PATCH", f"{API}/repos/{owner}/{name}", data={"private": True})
            print("已将仓库可见性纠正为 private")
        return
    body = {"name": name, "description": description,
            "private": private, "public": not private,
            "auto_init": False, "has_issues": True, "has_wiki": False}
    resp = api(token, "POST", f"{API}/user/repos", data=body)
    d = json.loads(resp)
    if "id" not in d:
        print("ERROR: 建仓失败:", d.get("message"), file=sys.stderr)
        for e in d.get("errors", []) or []:
            print("  -", e, file=sys.stderr)
        sys.exit(1)
    print("repo 创建:", d.get("full_name"), d.get("html_url"),
          f"(private={d.get('private')})")


def ensure_release(token, repo, tag, name, notes, prerelease=False):
    r = api(token, "GET", f"{API}/repos/{repo}/releases/tags/{tag}")
    rel = json.loads(r) if r else {}
    if "id" in rel:
        print("release 已存在, id:", rel["id"])
        if bool(rel.get("prerelease")) != bool(prerelease):
            api(token, "PATCH", f"{API}/repos/{repo}/releases/{rel['id']}",
                data={"prerelease": prerelease})
            print(f"prerelease 标记已纠正为 {prerelease}")
        return rel
    body = {"tag_name": tag, "name": name, "body": notes,
            "draft": False, "prerelease": prerelease}
    rel = json.loads(api(token, "POST", f"{API}/repos/{repo}/releases", data=body))
    print("release 已创建, id:", rel["id"])
    return rel


def delete_asset_by_name(token, repo, rid, name):
    """按名字查 id 再删 —— 绝不硬编码 asset id（曾因硬编码误删主资产）。"""
    r = api(token, "GET", f"{API}/repos/{repo}/releases/{rid}/assets?per_page=100")
    try:
        assets = json.loads(r)
    except Exception:
        return
    if not isinstance(assets, list):
        return
    for a in assets:
        if a.get("name") == name:
            api(token, "DELETE", f"{API}/repos/{repo}/releases/assets/{a['id']}")
            print(f"  已清理同名 asset id={a['id']}")
            return


def upload_one(token, repo, rid, path, name, rate_bps):
    """上传单个资产，带限速与 size 校验。返回 (ok, msg)。"""
    q = urllib.parse.quote(name, safe="")        # ★ 关键：中文/空格必须编码
    url = f"{UPLOAD}/repos/{repo}/releases/{rid}/assets?name={q}"
    rf = RateLimitedFile(path, rate_bps)
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/octet-stream",
        "Content-Length": str(rf.size),          # 显式长度，避免 chunked
        "User-Agent": "publish-release-script",
    }
    req = urllib.request.Request(url, data=rf, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=1800) as r:
            d = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}: {e.read().decode()[:300]}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"
    finally:
        rf.close()

    got = d.get("size")
    if d.get("state") != "uploaded" or got != rf.size:
        return False, f"size 不符 state={d.get('state')} 服务器={got} 本地={rf.size}"
    # ★ 服务器会静默剥离非 ASCII 名字，这里强校验
    if d.get("name") != name:
        return False, f"服务器保存名不符: 请求={name!r} 实际={d.get('name')!r}"
    return True, f"id={d.get('id')} {got} bytes"


def upload_assets(token, repo, rel, assets, force_rate=None, asset_name=None):
    existing = {a["name"]: a for a in rel.get("assets", [])}
    rid = rel["id"]
    all_ok = True

    if asset_name and len(assets) > 1:
        print("ERROR: --asset-name 只能配合单个资产使用", file=sys.stderr)
        return False

    for path in assets:
        raw_name = os.path.basename(path)
        if asset_name:
            name, renamed = asset_name, (asset_name != raw_name)
        else:
            name, renamed = ascii_asset_name(raw_name)
        if renamed:
            print(f"⚠ 文件名含非 ASCII 或已指定，GitHub 不支持中文资产名：")
            print(f"    原名: {raw_name}")
            print(f"    上传: {name}")

        if name in existing:
            a = existing[name]
            if a.get("size") == os.path.getsize(path):
                print(f"asset 已存在且大小一致，跳过: {name} ({a['size']} bytes)")
                continue
            print(f"asset 已存在但大小不符，先删除再传: {name}")
            delete_asset_by_name(token, repo, rid, name)

        fsize = os.path.getsize(path)
        is_large = fsize > LARGE_MB * 1024 * 1024
        print(f"\n上传: {name}  {fsize/1e6:.1f} MB"
              f"{'（大文件，将限速）' if is_large else ''}")

        # 大文件直接从 900k 起；小文件先不限速，失败后才降速
        ladder = list(RATE_LADDER) if is_large else [0] + RATE_LADDER[:-1]
        if force_rate is not None:
            ladder = [force_rate]

        ok = False
        for attempt in range(1, RETRIES + 1):
            rate = ladder[min(attempt - 1, len(ladder) - 1)]
            label = f"{rate//1024}KB/s" if rate else "不限速"
            print(f"  第 {attempt}/{RETRIES} 次（{label}）…", end=" ", flush=True)
            t0 = time.monotonic()
            ok, msg = upload_one(token, repo, rid, path, name, rate)
            if ok:
                print(f"OK  {msg}  耗时 {time.monotonic()-t0:.0f}s")
                break
            print(f"失败  {msg}")
            if attempt < RETRIES:
                delete_asset_by_name(token, repo, rid, name)   # 清理半成品
                time.sleep(3)
        if not ok:
            all_ok = False
            print(f"  ✗ {name} 三次均失败", file=sys.stderr)
    return all_ok


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True, help="owner/name")
    p.add_argument("--tag", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--notes", default="")
    p.add_argument("--dmgs", nargs="*", default=[], help="DMG file paths（兼容旧参数）")
    p.add_argument("--assets", nargs="*", default=[], help="任意资产文件路径")
    p.add_argument("--desc", default="")
    p.add_argument("--private", action="store_true",
                   help="create the repo as PRIVATE (default: public)")
    p.add_argument("--prerelease", action="store_true",
                   help="mark the release as prerelease (for -beta versions)")
    p.add_argument("--limit-rate", type=int, default=None, metavar="KBPS",
                   help="强制上传限速（KB/s）；默认大文件自动 900，0=不限速")
    p.add_argument("--asset-name", default=None,
                   help="显式指定资产在 Release 里的文件名（仅单资产时可用）。"
                        "GitHub 不支持中文资产名，中文名会被静默剥离，建议用它覆盖")
    args = p.parse_args()

    token = os.environ.get("TOKEN")
    if not token:
        print("ERROR: TOKEN env var not set", file=sys.stderr)
        sys.exit(1)

    owner, name = args.repo.split("/")
    ensure_repo(token, owner, name, args.desc, private=args.private)
    rel = ensure_release(token, args.repo, args.tag, args.name, args.notes,
                         prerelease=args.prerelease)

    files = list(args.dmgs) + list(args.assets)
    forced = None
    if args.limit_rate is not None:
        forced = args.limit_rate * 1024
    ok = upload_assets(token, args.repo, rel, files, force_rate=forced,
                       asset_name=args.asset_name)

    final = json.loads(api(token, "GET", f"{API}/repos/{args.repo}/releases/tags/{args.tag}"))
    print("\n=== 最终校验 ===")
    print("tag:", final.get("tag_name"))
    for a in final.get("assets", []):
        print(f"  - {a['name']}  {a['size']} bytes  state={a['state']}")
    print("html_url:", final.get("html_url"))
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
