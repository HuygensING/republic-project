# REPUBLIC Project

- [Documentation](#documentation)
- [Installation](#installation)
- [Usage](#usage)
- [Using code in jupyter notebooks](#running-republic-code-from-jupyter-notebooks)

- The resolutions are available via the [Goetgevonden](https://app.goetgevonden.nl/) search application. See https://goetgevonden.nl/en/ for more information on the project.


### The REPUBLIC project

Code for Huygens ING project REPUBLIC (REsolutions PUBlished In a Compuational Environment). The project creates an online computational platform to access the Resolutions of the Dutch States General.

The Resolutions of the Dutch States General (1576-1796) constitute an archival series that covers more than two centuries of continuous decision making and consists of more than 500,000 pages, handwritten and printed resolutions, in separate, chronologically ordered series.

The Resolutions of the States General in the Dutch Republic are a key resource to the political history of this period as they contain all decisions made by the States General (SG), the central ruling body in the Republic. It was designated as a key resource when in 1905 the work of publishing the resolutions started (Japikse et al. 1915). The manual editing resulted in two series of analogue publications of (a selection of) the resolutions, divided in an old series (14 volumes running from 1576 – 1609), a new series (7 volumes, 1610 – 1625), and a [digital edition (1626-1630)](http://resources.huygens.knaw.nl/retroboeken/statengeneraal).

The resolutions reveal the decision making process and are relevant for both high and low politics. They allow researchers to answer many different research questions about politics - but not only politics - in the Dutch Republic and its position in the world. The resolutions are also key to all the other records of the SG (about 1 mile) and form a backbone with which these other records can be connected and contextualised.

Project website: [https://republic.huygens.knaw.nl](https://republic.huygens.knaw.nl)

### Documentation

- [Parsing HTR/OCR output files](./docs/pagexml_scans.md)
- [Using phrase models and fuzzy search](./docs/phrase_models.md)


### Installation

Start by cloning the code base:
```shell
git clone git@github.com:HuygensING/republic-project.git
```

Next, creating a settings.py file with pointers to the various elasticsearch instances and databases. Copy the `settings-example.py` file and fill in the correct details (ask Marijn for details):
```shell
copy settings-example.py settings.py
```

Then, set up the virtual environment, installl required packages and fire up jupyter notebook:
```shell
pipenv --python 3.10
pipenv install -d
pipenv run jupyter notebook
```


### Usage

Retrieving documents from the different indexes:

```python

from republic.elastic.republic_elasticsearch import initialize_es

# initialise a RepublicElasticsearch instance that contains a
# config dictionary telling it what all the ES indexes are.
rep_es = initialize_es(host_type="external")

# Retrieve metadata for an inventory number
inv_num = 3820
inv_metadata = rep_es.retrieve_inventory_metadata(inv_num)

# Retrieve a page by its ID:
page = rep_es.retrieve_page_by_id('NL-HaNA_1.01.02_3820_0079-page-157')

# Retrieve all pages with resolutions for an inventory
inv_num = 3820
pages = rep_es.retrieve_inventory_resolution_pages(inv_num)

# Retrieve all sessions (line-based versions) for an inventory
inv_num = 3820
sessions = rep_es.retrieve_inventory_sessions_with_lines(inv_num)

# Retrieve all resolutions for an inventory
inv_num = 3820
resolutions = rep_es.retrieve_inventory_resolutions(inv_num)


```

### Running REPUBLIC code from jupyter notebooks

If you want to use any of the packages in notebooks in the `notebook` directory, you need to add the path to repository directory to your PATH variable:
```python
# This is needed to add the repo dir to the path so jupyter
# can load the republic modules directly from the notebooks
import os
import sys

repo_name = 'republic-project'
base_dir = os.path.split(os.getcwd())[0].split(repo_name)[0]
repo_dir = os.path.join(base_dir, repo_name)

print("adding project dir to path:", repo_dir)

if repo_dir not in sys.path:
    sys.path = [repo_dir] + sys.path
else:
    sys.path.remove(repo_dir)
    sys.path = [repo_dir] + sys.path
    

```
