'''
Author: Tahsin Hassan Rahit <kmtahsinhassan.rahit@ucalgary.ca>
Created: Thursday, December 8th 2022, 1:29:19 pm
-----
Copyright (c) 2022 Tahsin Hassan Rahit, MTG-lab, University of Calgary

You should have received a copy of the license along with this program.
'''
# python -m api.gpad


import typer
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
from rich import print
from dateutil import parser
from spacy import displacy
from datetime import date, timedelta
from spacy.matcher import PhraseMatcher

from .gene_discovery.models import *
from .gene_discovery.settings import *
from .gene_discovery.omim_api_extraction import extract_gene_info, get_gene_ids, has_update, ignore_existing_genes, get_geneMaps


tpr = typer.Typer()


@tpr.command()
def omim():
    # Get GeneMap entries
    # all_mims = get_geneMaps()
    
    # Identify Entries to fetch
    mims_to_fetch = []
    for gm in tqdm(GeneMap.objects, colour='#999999'):
        # TODO Batchwise processing
        update = has_update(gm)
        logging.info(f"{gm.mimNumber}: {update}")
        if update:
            mims_to_fetch.append(gm.mimNumber)
            for p in gm.phenotypes:
                mims_to_fetch.append(p.mim_number)
                
    # # Extract from OMIM API
    # to_ext = len(mims_to_fetch)
    # ext_limit = OMIM_DAILY_LIMIT * OMIM_RESPONSE_LIMIT
    # if to_ext > ext_limit:
    #     genes_to_extract = mims_to_fetch[:ext_limit]
    #     extract_gene_info(genes_to_extract, GeneEntry)
    # print(len(mims_to_fetch))
    print(f"[bold red]{len(mims_to_fetch)}[/bold red] genes.")
    

# @tpr.command()
# def process_omim():    
#     date_from = "0000"  # "to grab all use: 0000"
#     date_to = "*"  # "*" = now
#     if GeneEntry.objects:
#         print(GeneEntry.objects.count())
#         last_update_done_on = GeneEntry.objects().order_by('-dateUpdated').only('dateUpdated').first()['dateUpdated']
#         date_from = last_update_done_on.strftime("%Y/%m/%d")
    
#     print(f"Extracting gene IDs from {date_from} to {date_to}")
#     all_gene_ids = get_gene_ids('0000', date_to)
#     to_ext = len(all_gene_ids)
#     ext_limit = OMIM_DAILY_LIMIT * OMIM_RESPONSE_LIMIT
#     genes_to_extract = all_gene_ids
#     if to_ext > ext_limit:
#         gids_ua = ignore_existing_genes(all_gene_ids)
#         genes_to_extract = gids_ua[:ext_limit]
#         print(f"There are [bold red]{len(all_gene_ids)}[/bold red] entries will be extracted.")
#     print(f"[bold red]{len(genes_to_extract)}[/bold red] entries will be extracted.")
        
#     # if init:
#     #     all_gene_ids = get_gene_ids('0000', date_to)
#     #     genes_to_extract = ignore_existing_genes(all_gene_ids)

#     #     genes_to_extract = get_gene_ids(date_from, date_to)
#     # print(f"Total {len(genes_to_extract)} will be collected from API")
#     # extract_gene_info(genes_to_extract, GeneEntry)

if __name__ == '__main__':
    tpr()

