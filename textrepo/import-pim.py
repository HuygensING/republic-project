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

REPO = config['repo']



def main():
	print("Repo: " + REPO)

if __name__ == "__main__":
	main()
