import urllib.error
import urllib.request

UPSTREAM = "http://127.0.0.1:8799"

_HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}


def _read_body(environ):
    try:
        length = int(environ.get("CONTENT_LENGTH") or 0)
    except ValueError:
        length = 0
    return environ["wsgi.input"].read(length) if length > 0 else b""


def _headers(environ):
    headers = {}
    for key, value in environ.items():
        if key.startswith("HTTP_"):
            name = key[5:].replace("_", "-")
            if name.lower() not in _HOP_BY_HOP:
                headers[name] = value
    if environ.get("CONTENT_TYPE"):
        headers["Content-Type"] = environ["CONTENT_TYPE"]
    return headers


def application(environ, start_response):
    path = environ.get("PATH_INFO") or "/"
    query = environ.get("QUERY_STRING") or ""
    url = UPSTREAM + path + ("?" + query if query else "")
    method = environ.get("REQUEST_METHOD") or "GET"
    body = _read_body(environ)
    headers = _headers(environ)
    request = urllib.request.Request(
        url, data=body or None, headers=headers, method=method
    )
    try:
        response = urllib.request.urlopen(request, timeout=60)
        headers = [(k, v) for k, v in response.headers.items() if k.lower() not in _HOP_BY_HOP]
        status = f"{response.status} {response.reason}"
        body = response.read()
        response.close()
        start_response(status, headers)
        return [body]
    except urllib.error.HTTPError as error:
        headers = [(k, v) for k, v in error.headers.items() if k.lower() not in _HOP_BY_HOP]
        status = f"{error.code} {error.reason}"
        body = error.read()
        error.close()
        start_response(status, headers)
        return [body]