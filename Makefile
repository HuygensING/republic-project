
# make sure python 3.11 is installed
install_python:
	sudo add-apt-repository ppa:deadsnakes/ppa
	sudo apt update
	sudo apt install python3.11
	sudo apt install python3.11-distutils

setup_pip:
	# ensure latest pip is installed
	curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11
	# make a dir on mounted drive for python packages
	mkdir /data/vllmstorage/pip
	# make sure repository is cloned on mounted storage
	#cd /data/vllmstorage;git clone git@github.com:HuygensING/republic-project.git
	# make sure mounted drive dir is on PYTHONPATH
	echo 'export PYTHONPATH="/data/vllmstorage/pip/.local"' >> ~/.bashrc

# install pipenv using the correct pip
install_packages:
	python3.11 -m pip install "cython<3.0.0" wheel
	python3.11 -m pip install "pyyaml==5.4.1" --no-build-isolation
	python3.11 -m pip install pipenv --target /data/vllmstorage/pip/.local --cache-dir /data/vllmstorage/pip/.cache
	python3.11 -m pip install elasticsearch==7.15.0 pagexml-tools requests nltk bs4 numpy==1.26 pandas huggingface_hub==0.16.4 torch==2.1.0 transformers==4.31.0 accelerate==0.21.0 flair==0.12.2 --target /data/vllmstorage/pip/.local --cache-dir /data/vllmstorage/pip/.cache
	python3.11 -m pip install numpy==1.26 --target /data/vllmstorage/pip/.local --cache-dir /data/vllmstorage/pip/.cache


# create a virtual environment
setup_env:
	pipenv --python 3.11


make_dirs:
	mkdir data/paragraphs
	mkdir data/paragraphs/entities-Feb-2025
	mkdir data/entities
	mkdir data/entities/annotations-Feb-2025
	mkdir data/embeddings/fasttext
	mkdir resources
	mkdir resources/ner_taggers


