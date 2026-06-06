#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
import time
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

FEISHU_BASE = "https://open.feishu.cn/open-apis"
LARK_BASE = "https://open.larksuite.com/open-apis"
REDIRECT_URI = "http://localhost:9876/callback"
TOKEN_PATH = os.path.expanduser("~/.personal_feishu_user_token.json")
TOKEN_REFRESH_SKEW_SECONDS = 300


def load_local_env():
    env_path = os.path.join(os.getcwd(), ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_local_env()
APP_ID = os.environ.get("FEISHU_APP_ID", "")
APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")

OAUTH_SCOPES = " ".join([
    "offline_access",
    "minutes:minutes.search:read",
    "minutes:minutes:readonly",
    "minutes:minutes.transcript:export",
    "contact:user.base:readonly",
    "drive:drive:readonly",
    "docx:document",
    "search:docs:read",
    "calendar:calendar:readonly",
])


def out(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))


def die(error, message, details=None):
    payload = {"error": error, "message": message}
    if details:
        payload["details"] = details
    out(payload)
    sys.exit(1)


def require_creds():
    require_app_id()
    if not APP_SECRET:
        die("missing_credentials", "Set FEISHU_APP_SECRET.")


def require_app_id():
    if not APP_ID:
        die("missing_credentials", "Set FEISHU_APP_ID.")


def request_json(method, url, headers=None, payload=None):
    _, _, body = request_bytes(method, url, headers=headers, payload=payload)
    return json.loads(body.decode("utf-8"))


def request_bytes(method, url, headers=None, payload=None):
    body = None
    headers = dict(headers or {})
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers.setdefault("Content-Type", "application/json; charset=utf-8")
    req = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(req, timeout=30) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        try:
            details = json.loads(details)
        except json.JSONDecodeError:
            pass
        die("http_error", f"HTTP {exc.code} from Feishu.", details)


def get_app_access_token(base):
    require_creds()
    data = request_json("POST", f"{base}/auth/v3/app_access_token/internal", payload={
        "app_id": APP_ID,
        "app_secret": APP_SECRET,
    })
    if data.get("code") != 0:
        die("app_token_error", "Failed to get app_access_token.", data)
    return data["app_access_token"]


def load_token(valid_only=True):
    if not os.path.exists(TOKEN_PATH):
        return None
    with open(TOKEN_PATH) as f:
        cached = json.load(f)
    if not valid_only:
        return cached
    if cached.get("expire_time", 0) > time.time() + TOKEN_REFRESH_SKEW_SECONDS:
        return cached
    return None


def save_token(data):
    cached = {
        "user_access_token": data.get("access_token"),
        "refresh_token": data.get("refresh_token"),
        "expire_time": time.time() + data.get("expires_in", 7200),
        "refresh_expire_time": time.time() + data.get(
            "refresh_token_expires_in",
            data.get("refresh_expires_in", 0),
        ) if data.get("refresh_token") else 0,
        "open_id": data.get("open_id", ""),
        "user_id": data.get("user_id", ""),
        "name": data.get("name", ""),
        "scope": data.get("scope", ""),
        "token_type": data.get("token_type", "Bearer"),
    }
    with open(TOKEN_PATH, "w") as f:
        json.dump(cached, f, ensure_ascii=False, indent=2)
    return cached


def auth_status():
    cached_any = load_token(valid_only=False)
    cached = load_token(valid_only=True)
    out({
        "authenticated": bool(cached),
        "token_path": TOKEN_PATH,
        "has_token_cache": bool(cached_any),
        "has_refresh_token": bool(cached_any and cached_any.get("refresh_token")),
        "access_token_expires_in_seconds": int(cached_any.get("expire_time", 0) - time.time()) if cached_any else None,
        "refresh_token_expires_in_seconds": int(cached_any.get("refresh_expire_time", 0) - time.time()) if cached_any and cached_any.get("refresh_expire_time") else None,
        "scope": cached_any.get("scope", "") if cached_any else "",
        "user": cached_any.get("name", "") if cached_any else "",
    })


def oauth_url(base):
    require_app_id()
    url = (
        f"{base}/authen/v1/authorize"
        f"?app_id={APP_ID}"
        f"&redirect_uri={quote(REDIRECT_URI)}"
        f"&response_type=code"
        f"&state=personal_feishu_minutes"
        f"&scope={quote(OAUTH_SCOPES)}"
    )
    out({"auth_url": url, "redirect_uri": REDIRECT_URI})


def exchange_code(base, code):
    require_creds()
    data = request_json("POST", f"{base}/authen/v2/oauth/token", payload={
        "grant_type": "authorization_code",
        "client_id": APP_ID,
        "client_secret": APP_SECRET,
        "code": code,
        "redirect_uri": REDIRECT_URI,
    })
    if data.get("code") != 0:
        die("exchange_code_error", "Failed to exchange OAuth code.", data)
    cached = save_token(data)
    out({"authenticated": True, "token_path": TOKEN_PATH, "user": cached.get("name", "")})


def refresh_user_token(base):
    require_creds()
    cached = load_token(valid_only=False)
    if not cached or not cached.get("refresh_token"):
        die("missing_refresh_token", "No refresh_token cached. Add offline_access, publish app, and rerun OAuth.")
    if cached.get("refresh_expire_time", 0) and cached["refresh_expire_time"] <= time.time() + TOKEN_REFRESH_SKEW_SECONDS:
        die("refresh_token_expired", "Refresh token is expired or nearly expired. Rerun OAuth.")
    data = request_json("POST", f"{base}/authen/v2/oauth/token", payload={
        "grant_type": "refresh_token",
        "client_id": APP_ID,
        "client_secret": APP_SECRET,
        "refresh_token": cached["refresh_token"],
    })
    if data.get("code") != 0:
        die("refresh_token_error", "Failed to refresh user_access_token. Rerun OAuth if refresh_token was already used or expired.", data)
    refreshed = save_token(data)
    out({
        "authenticated": True,
        "refreshed": True,
        "token_path": TOKEN_PATH,
        "access_token_expires_in_seconds": int(refreshed.get("expire_time", 0) - time.time()),
        "refresh_token_expires_in_seconds": int(refreshed.get("refresh_expire_time", 0) - time.time()) if refreshed.get("refresh_expire_time") else None,
    })


def require_user_token():
    cached = load_token()
    if not cached:
        cached_any = load_token(valid_only=False)
        if cached_any and cached_any.get("refresh_token"):
            refresh_user_token(FEISHU_BASE)
            cached = load_token()
    if not cached:
        die("not_authenticated", "Run oauth_url and exchange_code first.")
    return cached["user_access_token"]


def extract_minute_token(value):
    patterns = [
        r"minutes/([A-Za-z0-9_-]+)",
        r"minute_token=([A-Za-z0-9_-]+)",
        r"([A-Za-z0-9_-]{16,})",
    ]
    for pattern in patterns:
        match = re.search(pattern, value)
        if match:
            return match.group(1)
    return value


def read_minute_transcript(base, minute_token):
    token = require_user_token()
    minute_token = extract_minute_token(minute_token)
    params = urlencode({
        "need_speaker": "true",
        "need_timestamp": "true",
        "file_format": "txt",
    })
    url = f"{base}/minutes/v1/minutes/{minute_token}/transcript?{params}"
    _, headers, body = request_bytes("GET", url, headers={"Authorization": f"Bearer {token}"})
    content_type = headers.get("Content-Type", "")
    text = body.decode("utf-8", errors="replace")
    if "application/json" in content_type:
        data = json.loads(text)
        if data.get("code") != 0:
            die("minute_transcript_error", "Failed to read transcript. Use exported transcript fallback.", data)
    out({
        "source": "feishu_minutes",
        "minute_token": minute_token,
        "transcript_text": text,
    })


def search_minutes(base, query, page_size, page_token, start, end):
    token = require_user_token()
    params = {
        "page_size": str(page_size),
        "user_id_type": "open_id",
    }
    if page_token:
        params["page_token"] = page_token
    payload = {}
    if query:
        payload["query"] = query
    if start or end:
        create_time = {}
        if start:
            create_time["start_time"] = start
        if end:
            create_time["end_time"] = end
        payload["filter"] = {"create_time": create_time}
    payload["sorter"] = "create_time_desc"
    url = f"{base}/minutes/v1/minutes/search?{urlencode(params)}"
    data = request_json("POST", url, headers={"Authorization": f"Bearer {token}"}, payload=payload)
    if data.get("code") != 0:
        die("search_minutes_error", "Failed to search Feishu minutes.", data)
    out({
        "source": "feishu_minutes",
        "query": query,
        "raw": data.get("data", data),
    })


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", required=True, choices=[
        "auth_status",
        "oauth_url",
        "exchange_code",
        "refresh_token",
        "search_minutes",
        "read_minute_transcript",
    ])
    parser.add_argument("--auth-code")
    parser.add_argument("--minute-token")
    parser.add_argument("--query", default="")
    parser.add_argument("--page-size", type=int, default=10)
    parser.add_argument("--page-token", default="")
    parser.add_argument("--start", default="")
    parser.add_argument("--end", default="")
    parser.add_argument("--use-lark", action="store_true")
    args = parser.parse_args()
    base = LARK_BASE if args.use_lark else FEISHU_BASE
    if args.action == "auth_status":
        auth_status()
    elif args.action == "oauth_url":
        oauth_url(base)
    elif args.action == "exchange_code":
        if not args.auth_code:
            die("missing_param", "--auth-code is required.")
        exchange_code(base, args.auth_code)
    elif args.action == "refresh_token":
        refresh_user_token(base)
    elif args.action == "search_minutes":
        search_minutes(base, args.query, args.page_size, args.page_token, args.start, args.end)
    elif args.action == "read_minute_transcript":
        if not args.minute_token:
            die("missing_param", "--minute-token is required.")
        read_minute_transcript(base, args.minute_token)


if __name__ == "__main__":
    main()
