#!/usr/bin/env python3

#pip3 install tqdm
from tqdm import tqdm

import os
import requests
import sys
import yaml

if (len(sys.argv) <= 1):
	print('please pass config file name as first argument')
	sys.exit()

with open(sys.argv[1]) as ymlfile:
	config = yaml.load(ymlfile, Loader=yaml.FullLoader)

PIM_AUTH = config['pim_auth']
AUTH_HDR = {'Authorization': PIM_AUTH}

PIM_BASE = config['pim_base']
PIM_DOCS = PIM_BASE + config['pim_docs']

PIM_IMGS = PIM_DOCS + config['pim_imgs']

TXT_REPO = config['txt_repo']


def fetch_document_image_set(session):
	req = requests.Request('GET', PIM_DOCS, headers=AUTH_HDR).prepare()
	resp = session.send(req)
	resp.raise_for_status()
	if resp.status_code == 200:
		print("Got document image set")
	return resp.json()

def is_republic(doc):
	if doc['elasticSearchIndex'] == None:
		return False
	return doc['elasticSearchIndex']['name'] == 'republic'

def fetch_image_set(session, uuid):
	url = PIM_IMGS.format(id = uuid)
	print("Fetching: " + url)
	req = requests.Request('GET', url=url, headers=AUTH_HDR).prepare()
	resp = session.send(req)
	resp.raise_for_status()
	return resp.json()

def extract_id(uri):
	"""Extract externalId from remoteuri"""
	parts = uri.split('/')
	num = len(parts)
	assert(num > 1)
	file = parts[num - 1]
	return os.path.splitext(file)[0]

def external_id_exists(session, externalId):
	url = TXT_REPO + '/documents'
	params = {'externalId': externalId}
	req = requests.Request('GET', url=url, params=params).prepare()
	resp = session.send(req)
	resp.raise_for_status()
	if resp.status_code != 200:
		return False
	json = resp.json()
	if json['total'] == 0:
		return False
	return json['items'][0]['externalId'] == externalId

def register_external_id(session, externalId):
	url = TXT_REPO + '/documents'
	payload = {'externalId': externalId}
	req = requests.Request('POST', url=url, json=payload).prepare()
	resp = session.send(req)
	resp.raise_for_status()
	return resp.json()

def main():
	print("PIM_DOCS: " + PIM_DOCS)
	print("PIM_IMGS: " + PIM_IMGS)
	print("Text Repo: " + TXT_REPO)

	with requests.Session() as session:
		docs = fetch_document_image_set(session)
		republic_docs = list(filter(is_republic, docs))
		for doc in republic_docs:
			img_set = fetch_image_set(session, doc['uuid'])
			for img in img_set:
				externalId = extract_id(img['remoteuri'])
				if external_id_exists(session, externalId):
					print("externalId: " + externalId + " already exists")
				else:
					print("registering externalId: " + externalId)
					res = register_external_id(session, externalId)
					print(res)
			sys.exit(0) # early exit during development

if __name__ == "__main__":
	main()
