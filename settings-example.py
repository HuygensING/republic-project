host = "localhost"
port = 9200
url_prefix = None

config = {
    "elastic_config": {
        "host": host,
        "port": port,
        "url_prefix": url_prefix,
        "url": f"http://{host}:{port}/" + f"{url_prefix}/" if url_prefix else ""
    }
}

