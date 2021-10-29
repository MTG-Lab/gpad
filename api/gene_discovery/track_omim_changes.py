'''
Author: Tahsin Hassan Rahit <kmtahsinhassan.rahit@ucalgary.ca>
Created: Wednesday, April 14th 2021, 2:58:30 pm
-----
Copyright (c) 2021 Tahsin Hassan Rahit, MTG-lab, University of Calgary

You should have received a copy of the license along with this program.
'''


import datetime
import json
import logging
import re
import math
import time
from numpy import empty
from tqdm import tqdm, trange
from pathlib import Path

import pandas as pd
import requests
import spacy
from dateutil import parser
from spacy import displacy
from datetime import date, timedelta
from mongoengine.queryset.visitor import Q
from spacy.matcher import PhraseMatcher

from .models import *
from .settings import *


# prev_gene_mims = [
#     e.gene_mim_id for e in EarliestPhenotypeEvidences.objects.only('gene_mim_id')]
# print("NEW GENE")
# new_genes = UpdatedAssociationEvidences.objects(gene_mim_id__nin=prev_gene_mims)
# for entry in new_genes:
#     print(f"New phenotype for: {entry.gene_mim_id}, {entry.phenotype_mim}")
# new_gene_mims = [e.gene_mim_id for e in new_genes]
# new_gene_mims = list(set(new_gene_mims))
# print(new_gene_mims)
# print("UPDATES")
from_date = datetime.datetime(2021, 5, 1)
updated_genes = UpdatedAssociationEvidences.objects(date_updated__gte=from_date)
for entry in updated_genes:
    # print(f"gene: {entry.gene_mim_id}, pheno: {entry.phenotype_mim}, date: {entry.date_updated}")
    prev_update = UpdatedAssociationEvidences.objects(
        Q(gene_mim_id=entry.gene_mim_id) &
        Q(phenotype_mim=entry.phenotype_mim) &
        Q (date_updated__lt=from_date)
    ).order_by('-date_updated').first()
    if not prev_update:
        prev_update = EarliestPhenotypeEvidences.objects(
            Q(gene_mim_id=entry.gene_mim_id) &
            Q(phenotype_mim=entry.phenotype_mim)
        ).first()
    if not prev_update:
        print(f"New phenotype for: {entry.gene_mim_id}, {entry.phenotype_mim}")

    # else:
    #     print(f"gene: {prev_update.gene_mim_id}, pheno: {prev_update.phenotype_mim}, date: {prev_update.date_updated}\n")

    
    # """
    # Case 1: Track what new publication has been added. Backtrack to check if it is associated with any cohort, matacher, population or animal study.
    # Case 2: Q: Do we need to check if there is a new assocation made in already associated gene-pheno pair? or we just look for new gene-pheno association?

    # Algo:
    # origin study set - updated study set = This new set should indicate updated studies!
    # """
