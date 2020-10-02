host_internal = 'local'
host_external = '<your-external-url>'
text_repo_url = '<url-for-text-repo-service>'
data_host_url = '<host.for.downloading.ocr/htr.data>'
url_prefix = '<url-prefix-for-elasticsearch>'


def set_elasticsearch_config(host_type: str = 'internal'):
    host = host_internal if host_type == 'internal' else host_external
    scheme = 'http' if host_type == 'internal' else 'https'
    port = 80 if scheme == 'http' else 443
    config = {
        'elastic_config': {
            'host': host,
            'port': port,
            'scheme': scheme,
            'url_prefix': url_prefix,
            'url': f'{scheme}://{host}:{port}/' + f'{url_prefix}/' if url_prefix else ''
        },
        'data_host': {
            'host_url': data_host_url
        },
        'text_repo': {
            'api_url': text_repo_url
        }
    }
    return config

