'''
Author: Tahsin Hassan Rahit <kmtahsinhassan.rahit@ucalgary.ca>
Created: Thursday, April 15th 2021, 12:49:03 pm
-----
Copyright (c) 2021 Tahsin Hassan Rahit, MTG-lab, University of Calgary

You should have received a copy of the license along with this program.
'''



import click
import datetime
import json
import logging
import re
import math
import time
from pymongo.uri_parser import split_options
from tqdm import tqdm, trange
from pathlib import Path

import random
import pandas as pd
import requests
import spacy
from dateutil import parser
from spacy import displacy
from datetime import date, timedelta
from spacy.matcher import PhraseMatcher
import xml.etree.ElementTree as ET

from .models import *
from .settings import *


for entry in tqdm(GeneEntry.objects):
    if entry.referenceList:
        pmids = [ref['reference']['pubmedID'] for ref in entry.referenceList if 'pubmedID' in ref['reference']]
        already_exists = NCBIEntry.objects(pmid__in=pmids).only('pmid')
        pmids_already_exists = [article.pmid for article in already_exists]
        pmids_to_extract = list(set(pmids) - set(pmids_already_exists))
        if pmids_to_extract:
            response = requests.get(
                'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi',
                params={
                    'id': ','.join(str(pmid) for pmid in pmids_to_extract),
                    'db': 'pubmed',
                    'retmode': 'xml',
                    'rettype': 'pubmed',
                    'tool': 'gene_discovery_analyzer'
                },
                headers={'api_key': NCBI_API_KEY},
            )
            if response.content:
                pubmed_articles = ET.fromstring(response.content)
                for pubmed_article in pubmed_articles.iter('PubmedArticle'):
                    pmid = pubmed_article.find('MedlineCitation//PMID').text
                    abstract_dom = pubmed_article.find('MedlineCitation//Abstract//AbstractText')
                    ncbi_entry = NCBIEntry.objects(pmid=pmid).only('pmid').first()
                    if not ncbi_entry and pmid and abstract_dom:
                        ncbi_entry = NCBIEntry()
                        ncbi_entry['pmid'] = pmid
                        ncbi_entry['abstract'] = abstract_dom.text
                        ncbi_entry.save()
            time.sleep(0.5)   # NCBI allows 3 (without API key) and 10 (with API key) requests per seconds.

