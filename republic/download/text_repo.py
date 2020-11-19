from typing import Dict, List, Union
import gzip
import requests


def make_request(url: str, accept_encoding: Union[None, str] = None) -> Union[List[dict], dict, str]:
    headers = {}
    if accept_encoding:
        headers = {'Accept-encoding': accept_encoding}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        if response.headers['Content-Type'] == 'application/json':
            return response.json()
        if 'Content-Encoding' not in response.headers:
            #print('missing encoding property for url', url)
            #try:
            #    return gzip.decompress(response.content).decode(encoding='utf-8')
            #except (OSError, TypeError):
            #    pass
            return response.text
        if response.headers['Content-Encoding'] == 'gzip':
            return gzip.decompress(response.content).decode(encoding='utf-8')
        else:
            return response.text
    else:
        raise ValueError(response.content)


class TextRepo:

    def __init__(self, api_url: str):
        self.api_url = api_url
        self.type_name = {}
        self.type_id = {}
        self.documents_url = api_url + '/rest/documents'
        self.get_types()

    def get_types(self) -> None:
        """Check TextRepo for the available file types and their IDs."""
        data: List[Dict[str, str]] = make_request(self.api_url + '/rest/types')
        print(data)
        for type_info in data:
            print(type_info)
            self.type_id[type_info['name']] = type_info['id']
            self.type_name[type_info['id']] = type_info['name']

    def get_type_name(self, type_id: str) -> str:
        """Return the corresponding file_type name for a given file_type ID."""
        if type_id not in self.type_name:
            raise KeyError('Unknown type_id')
        return self.type_name[type_id]

    def get_type_id(self, type_name: str) -> str:
        """Return the corresponding file_type ID for a given file_type name."""
        if type_name not in self.type_id:
            raise KeyError('Unknown type_name')
        return self.type_id[type_name]

    def get_internal_id(self, external_id: str) -> str:
        """Return the TextRepo internal document ID for a given external ID"""
        url = self.documents_url + f'?externalId={external_id}'
        data: Dict[str, List[Dict[str, str]]] = make_request(url)
        return data['items'][0]['id']

    def get_document_metadata(self, external_id, content_type) -> str:
        """Return document metadata for a given external ID."""
        endpoint = f'/task/find/{external_id}/document/metadata?type={content_type}'
        return make_request(self.api_url + endpoint)

    def get_last_version_content(self, external_id: str, file_type: str) -> str:
        """Return the content of the latest version of a given external ID and file type.

        :param external_id: an external document ID
        :type external_id: str
        :param file_type: the name of the file type
        :type file_type: str
        :return: The file content of the requested file
        :rtype: str
        """
        endpoint = f'/task/find/{external_id}/file/contents?type={file_type}'
        url = self.api_url + endpoint
        try:
            return make_request(url, accept_encoding="gzip")
        except ConnectionError:
            return None

    def get_file_info(self, external_id: str) -> Dict[str, Union[str, List[Dict[str, str]]]]:
        """Return information on the available files for a given external ID."""
        internal_id = self.get_internal_id(external_id)
        url = self.documents_url + f'/{internal_id}/files'
        data: Dict[str, List[Dict[str, str]]] = make_request(url)
        for item in data['items']:
            item['type'] = self.get_type_name(item['typeId'])
        return data

    def get_file_type_id(self, external_id: str, file_type: str) -> Union[None, str]:
        """Return the file id for a given external document ID and a given file type."""
        file_info = self.get_file_info(external_id)
        for item in file_info['items']:
            if item['type'] == file_type:
                return item['id']
        return None

    def get_file_type_versions(self, external_id: str, file_type: str) -> Dict[str, Union[str, List[Dict[str, str]]]]:
        """Return information on the available file versions for a given external document ID and a given file type."""
        file_id = self.get_file_type_id(external_id, file_type)
        url = self.api_url + f'/rest/files/{file_id}/versions'
        return make_request(url)

    def get_content_by_version_id(self, version_id: str) -> str:
        """Return content of a version of a file given a version ID."""
        url = self.api_url + f'/rest/versions/{version_id}/contents'
        return make_request(url, accept_encoding="gzip")

    def get_last_version_info(self, scan_id, file_type: str) -> Dict[str, str]:
        """Return information on the the latest available file version
        for a given external document ID and a given file type."""
        versions = self.get_file_type_versions(scan_id, file_type)
        return sorted(versions['items'], key=lambda x: x['createdAt'], reverse=True)[0]

