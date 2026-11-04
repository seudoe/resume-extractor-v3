# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pynacl>=1.5.0",
# ]
# ///
"""Push GitHub Actions repo secrets from .env.repo (HF_* variables) to GitHub repository.

Usage:
    uv run scripts/push_repo_secrets.py [--dry]
    python scripts/push_repo_secrets.py [--dry]
"""

import argparse
import json
import os
import re
import sys
from base64 import b64encode
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ENV_FILE = ROOT / ".env.repo"
DEFAULT_REPO = os.environ.get("GH_REPO", "seudoe/resume-extractor-v3")


def parse_env_file(path: Path) -> tuple[str | None, dict[str, str]]:
    """Parse .env.repo for GH_TOKEN and non-empty HF_* secrets."""
    if not path.exists():
        print(f"[Error] Env file not found: {path}", file=sys.stderr)
        sys.exit(1)

    content = path.read_text(encoding="utf-8")
    gh_token = None
    m_gh = re.search(r"^\s*GH_TOKEN\s*=\s*[\"']?([^\"'\r\n]+)", content, re.MULTILINE)
    if m_gh:
        gh_token = m_gh.group(1).strip()

    secrets: dict[str, str] = {}
    pairs: list[dict[str, str]] = []
    current_pair: dict[str, str] = {}

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^([A-Za-z0-9_]+)\s*=\s*(.*)$", line)
        if not m:
            continue
        k = m.group(1).strip()
        v = m.group(2).strip().strip("\"'")
        if not v:
            continue

        if k.startswith("HF_"):
            secrets[k] = v
            if k.startswith("HF_USER_"):
                current_pair["user"] = v
            elif k.startswith("HF_TOKEN_"):
                current_pair["token"] = v

            if "user" in current_pair and "token" in current_pair:
                pairs.append(dict(current_pair))
                current_pair.clear()

    # Alias first account as HF_USER_1 / HF_TOKEN_1 if not already explicit
    for idx, p in enumerate(pairs, start=1):
        secrets.setdefault(f"HF_USER_{idx}", p["user"])
        secrets.setdefault(f"HF_TOKEN_{idx}", p["token"])

    return gh_token, secrets


def encrypt_secret(public_key_b64: str, secret_value: str) -> str:
    """Encrypt a secret using libsodium sealed box with the repository public key."""
    try:
        from nacl import encoding, public
    except ImportError:
        print("[Error] PyNaCl is required. Run with:\n    uv run scripts/push_repo_secrets.py\n or:\n    pip install pynacl", file=sys.stderr)
        sys.exit(1)

    pk = public.PublicKey(public_key_b64.encode("utf-8"), encoding.Base64Encoder)
    sealed_box = public.SealedBox(pk)
    encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
    return b64encode(encrypted).decode("utf-8")


def gh_api_request(url: str, token: str, method: str = "GET", data: dict | None = None) -> dict:
    """Perform GitHub Actions REST API request."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "resume-extractor-v3-secret-sync",
    }
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = Request(url, data=body, headers=headers, method=method)

    try:
        with urlopen(req) as resp:
            raw = resp.read()
            return json.loads(raw.decode("utf-8")) if raw else {}
    except HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        try:
            return {"_status": e.code, **json.loads(err_body)}
        except Exception:
            return {"_status": e.code, "message": err_body}


def main():
    parser = argparse.ArgumentParser(description="Push HF secrets from .env.repo to GitHub Actions")
    parser.add_argument("--dry", action="store_true", help="Print secrets that would be set without uploading")
    parser.add_argument("--repo", default=DEFAULT_REPO, help=f"GitHub repository (default: {DEFAULT_REPO})")
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE, help=f"Path to .env.repo (default: {DEFAULT_ENV_FILE})")
    args = parser.parse_args()

    gh_token, secrets = parse_env_file(args.env_file)
    gh_token = os.environ.get("GH_TOKEN") or gh_token

    if not gh_token and not args.dry:
        print(f"[Error] GH_TOKEN not found in {args.env_file} or environment.", file=sys.stderr)
        sys.exit(1)

    if not secrets:
        print(f"No non-empty HF_* secrets found in {args.env_file}.")
        return

    if args.dry:
        print(f"[DRY RUN] Target Repository: {args.repo}")
        for k, v in secrets.items():
            print(f"  would set {k} ({len(v)} chars)")
        return

    # 1. Fetch public key
    print(f"Fetching public key for {args.repo}...")
    api_base = f"https://api.github.com/repos/{args.repo}/actions/secrets"
    pk_data = gh_api_request(f"{api_base}/public-key", gh_token)

    if "_status" in pk_data and pk_data["_status"] != 200 or "key" not in pk_data:
        print(f"\n[Error] Unable to get repository public key from GitHub (HTTP {pk_data.get('_status')}):", file=sys.stderr)
        print(json.dumps(pk_data, indent=2), file=sys.stderr)
        if "Resource not accessible by personal access token" in pk_data.get("message", ""):
            print(f"""
--------------------------------------------------------------------------------
Your Personal Access Token (GH_TOKEN) does not have access to repo: "{args.repo}".

To fix this:
1. Go to GitHub: https://github.com/settings/tokens
2. Under "Fine-grained tokens", click your token.
3. In "Repository access", ensure "{args.repo}" is selected.
4. Under "Repository permissions", set "Secrets" to Read and Write.
5. Save changes and re-run this script.
--------------------------------------------------------------------------------""", file=sys.stderr)
        sys.exit(1)

    public_key = pk_data["key"]
    key_id = pk_data["key_id"]

    # 2. Encrypt and upload secrets
    print(f"Encrypting and uploading {len(secrets)} secrets to {args.repo}...")
    success = 0
    for name, value in secrets.items():
        encrypted_val = encrypt_secret(public_key, value)
        payload = {
            "encrypted_value": encrypted_val,
            "key_id": key_id,
        }
        res = gh_api_request(f"{api_base}/{name}", gh_token, method="PUT", data=payload)
        if res.get("_status") in (None, 201, 204):
            print(f"  ✓ set {name}")
            success += 1
        else:
            print(f"  ✗ FAILED {name} (HTTP {res.get('_status')}): {res.get('message')}", file=sys.stderr)

    print(f"\nDone. Successfully set {success}/{len(secrets)} secrets.")


if __name__ == "__main__":
    main()
