from pathlib import Path

from bbwebscan.models import AuthConfig


def parse_header_values(values: list[str]) -> dict[str, str]:
    headers: dict[str, str] = {}
    for value in values:
        if ":" not in value:
            raise ValueError(f"Invalid header value (missing ':'): {value}")
        key, header_value = value.split(":", 1)
        key_clean = key.strip()
        if not key_clean:
            raise ValueError(f"Invalid header value (empty name): {value}")
        headers[key_clean] = header_value.strip()
    return headers


def parse_cookie_values(values: list[str]) -> dict[str, str]:
    cookies: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"Invalid cookie value (missing '='): {value}")
        key, cookie_value = value.split("=", 1)
        key_clean = key.strip()
        if not key_clean:
            raise ValueError(f"Invalid cookie value (empty name): {value}")
        cookies[key_clean] = cookie_value.strip()
    return cookies


def merge_auth(
    base_auth: AuthConfig,
    headers: list[str],
    cookies: list[str],
    raw_request: str | None,
) -> AuthConfig:
    merged_headers = dict(base_auth.headers)
    merged_headers.update(parse_header_values(headers))
    merged_cookies = dict(base_auth.cookies)
    merged_cookies.update(parse_cookie_values(cookies))
    raw_path = Path(raw_request) if raw_request else base_auth.raw_request
    return AuthConfig(headers=merged_headers, cookies=merged_cookies, raw_request=raw_path)


def build_header_lines(auth: AuthConfig) -> list[str]:
    lines = [f"{key}: {value}" for key, value in sorted(auth.headers.items())]
    cookie_header = auth.cookie_header()
    if cookie_header is not None:
        lines.append(f"Cookie: {cookie_header}")
    return lines


def build_header_args(auth: AuthConfig, flag: str = "-H") -> list[str]:
    args: list[str] = []
    for header_line in build_header_lines(auth):
        args.extend([flag, header_line])
    return args
