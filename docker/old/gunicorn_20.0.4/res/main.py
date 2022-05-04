def app(environ, start_response):
    data = b"<h1>Gunicorn 20.0.4: Smuggling Test.</h1>\n"
    start_response("200 OK", [
        ("Content-Type", "text/plain"),
        ("Content-Length", str(len(data)))
    ])
    return iter([data])
