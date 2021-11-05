
'''
Author: Tahsin Hassan Rahit <kmtahsinhassan.rahit@ucalgary.ca>
Created: Friday, March 5th 2021, 11:04:37 am
-----
Copyright (c) 2021 Tahsin Hassan Rahit, MTG-lab, University of Calgary

You should have received a copy of the license along with this program.
'''
# python -m api.gene_discovery.omim_api_extraction

import click
import datetime
import json
import logging
import re
import math
import time
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

from .models import *
from .settings import *


def get_gene_ids(date_from, date_to):
    """ Getting the gene mim ids from OMIM api using date range

    Args:
        date_from ([type]): start date. Use 0000 to start from earliest. See doc: 
        date_to ([type]): End date. See doc: 
    """
    print(f"Extracting gene IDs from {date_from} to {date_to}")
    more_page = True
    start_idx = 0
    total_result = 1
    all_gene_ids = []
    while more_page and total_result:
        response = requests.get(
            'https://api.omim.org/api/entry/search',
            params={
                'search': f'date_created:{date_from}-{date_to} OR date_updated:{date_from}-{date_to}',
                'start': start_idx,
                'sort': 'date_updated+asc',
                'limit': OMIM_RESPONSE_LIMIT,
                'format': 'json'
            },
            headers={'ApiKey': OMIM_API_KEY},
        )
        _entries = response.json()['omim']['searchResponse']['entryList']
        _gene_ids = [int(_e['entry']['mimNumber']) for _e in _entries]
        all_gene_ids += _gene_ids
        # Paging
        total_result = response.json()['omim']['searchResponse']['totalResults']
        end_idx = response.json()['omim']['searchResponse']['endIndex']
        start_idx = end_idx + 1 # random.randint(1, 30)
        more_page = total_result > start_idx
    print(f"Total gene between {date_from} to {date_to}: {len(all_gene_ids)}")
    return all_gene_ids

def ignore_existing_genes(all_gene_ids):
    # Ignore genes that are already extracted (for initial data extraction. Should not be used when tracking update)
    already_exists = GeneEntry.objects(mimNumber__in=all_gene_ids).only('mimNumber')
    mim_ids_already_exists = [gene.mimNumber for gene in already_exists]
    genes_to_extract = list(set(all_gene_ids) - set(mim_ids_already_exists))
    print(f"Total gene count {len(all_gene_ids)} of which {len(mim_ids_already_exists)} are already exist in the DB.")
    return genes_to_extract

def extract_gene_info(genes_to_extract, entry_class=GeneEntry):
    gene_count = len(genes_to_extract)
    for i in trange(int(math.ceil(gene_count/OMIM_RESPONSE_LIMIT)), desc='overall'):
        # print(f"Page {i}")
        omim_genes = genes_to_extract[i*OMIM_RESPONSE_LIMIT:(i+1)*OMIM_RESPONSE_LIMIT] 
        response = requests.get(
            'https://api.omim.org/api/entry',
            params={
                'mimNumber': ','.join(str(m) for m in omim_genes),
                'include': 'text,allelicVariantList,geneMap,referenceList,externalLinks,dates,editHistory,creationDate',
                'format': 'json'
            },
            headers={'ApiKey': OMIM_API_KEY},
        )
        response_entries = response.json()['omim']['entryList']
        for r in response_entries:
            # existing_entry = GeneEntry.objects(
            #     mimNumber=r['entry']['mimNumber']).first()
            entry = entry_class()
            entry["mimNumber"] = r['entry']['mimNumber']
            entry["status"] = r['entry']['status']
            entry["titles"] = r['entry']['titles']
            entry["creationDate"] = r['entry']['creationDate']
            entry["editHistory"] = r['entry']['editHistory']
            entry["epochCreated"] = r['entry']['epochCreated']
            entry["dateCreated"] = r['entry']['dateCreated']
            entry["epochUpdated"] = r['entry']['epochUpdated']
            entry["dateUpdated"] = r['entry']['dateUpdated']
            if 'prefix' in r['entry']:
                entry["prefix"] = r['entry']['prefix']
            if 'geneMap' in r['entry']:
                entry["geneMap"] = r['entry']['geneMap']
            if 'textSectionList' in r['entry']:
                entry["textSectionList"] = r['entry']['textSectionList']
            if 'allelicVariantList' in r['entry']:
                entry["allelicVariantList"] = r['entry']['allelicVariantList']
            if 'referenceList' in r['entry']:
                entry["referenceList"] = r['entry']['referenceList']
            if 'externalLinks' in r['entry']:
                entry["externalLinks"] = r['entry']['externalLinks']
            entry["mtgUpdated"] = datetime.datetime.now()
            # if existing_entry is None:
            entry["mtgCreated"] = datetime.datetime.now()
            # else:
            #     entry["mtgCreated"] = existing_entry.mtgCreated
            #     existing_entry.update(set__mtgUpdated = datetime.datetime.now())
            entry.save()


@click.command()
@click.option('--init', is_flag=True, help='Initialize/Freeze current OMIM data')
def extract_from_omim(init):
    date_from = "2021/04/13"  # "to grab all use: 0000"
    date_to = "*"  # "*" = now
    
    if init:
        all_gene_ids = get_gene_ids('0000', date_to)
        genes_to_extract = ignore_existing_genes(all_gene_ids)
    else:
        if GeneEntry.objects:
            last_update_done_on = GeneEntry.objects().order_by('-dateUpdated').only('dateUpdated').first()['dateUpdated']
            date_from = last_update_done_on.strftime("%Y/%m/%d")        
        genes_to_extract = get_gene_ids(date_from, date_to)
    print(f"Total {len(genes_to_extract)} will be collected from API")
    extract_gene_info(genes_to_extract, GeneEntry)

if __name__ == '__main__':
    extract_from_omim()