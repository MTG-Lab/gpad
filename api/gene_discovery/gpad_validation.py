'''
Author: Tahsin Hassan Rahit <kmtahsinhassan.rahit@ucalgary.ca>
Created: Thursday, June 10th 2021, 12:10:59 pm
-----
Copyright (c) 2021 Tahsin Hassan Rahit, MTG-lab, University of Calgary

You should have received a copy of the license along with this program.
'''

from unittest import result
import pandas as pd
import numpy as np
from pathlib import Path
import pprint
from tqdm import tqdm
from api.gene_discovery.settings import db, data_dir

# python -m api.gene_discovery.consistancy_validation

# 3862 


df = pd.read_csv(data_dir / 'Gene-RD-Provenance_V2.1.txt', sep='\t').dropna(subset=["ENSID"])
df = df.fillna(0)
query = {'mapping_key': {'$ne': 2}}
entries = db.latest.find(query)
df['Disease OMIM ID'] = [int(row['Disease OMIM ID']) for idx, row in df.iterrows()]
df['PMID Gene-disease'] = [int(row['PMID Gene-disease']) for idx, row in df.iterrows()]

result_array = []
total_entries = db.latest.count_documents(query)
i = 0

result = {True: 0, False: 0, 'NA': 0, 'NOASSOC': 0}
for entry in tqdm(entries, total=total_entries):
    
    gene_entry = db.gene_entry.find_one({'mimNumber': entry['gene_mim_id']})
    ensemble_ids = []
    if 'geneMap' in gene_entry and 'ensemblIDs' in gene_entry['geneMap']:
        ensemble_ids = gene_entry['geneMap']['ensemblIDs'].split(',')
    ehrhart_rows = df[(df['ENSID'].isin(ensemble_ids)) & (df['Disease OMIM ID']==entry['phenotype_mim'])]
    
    ehrhart = False
    pmid = 'GPADUA'
    year = 0
    if 'earliest_phenotype_association' in entry and 'year' in entry['earliest_phenotype_association']:
        year = entry['earliest_phenotype_association']['year']
        if  'pmid' in entry['earliest_phenotype_association']:
            pmid = entry['earliest_phenotype_association']['pmid']
        else:
            pmid = 'NA'
    else:
        ehrhart = 'NOASSOC' # No evidence available on GPAD
    
    if ehrhart != 'NOASSOC' and len(ehrhart_rows.index):
        # Evidence available in ehrhart
        for idx, row in ehrhart_rows.iterrows():
            if row['PMID Gene-disease'] == pmid:
                # match publication
                result_array.append([entry['gene_mim_id'], entry['phenotype_mim'], pmid, year, row['PMID Gene-disease']])
                ehrhart = True
                break
    elif ehrhart == 'NOASSOC':
        # Evidence not available on GPAD
        result_array.append([entry['gene_mim_id'], entry['phenotype_mim'], pmid, year, len(ehrhart_rows.index) > 0])
    else:
        # Evidence not available in Ehrhart
        result_array.append([entry['gene_mim_id'], entry['phenotype_mim'], pmid, year, 'NA'])
        ehrhart = 'NA'
    if ehrhart == False:
        # PMID does not match with ehrhart
        result_array.append([entry['gene_mim_id'], entry['phenotype_mim'], pmid, year, False])
    result[ehrhart] += 1
        
result_df = pd.DataFrame(result_array)
result_df.to_csv(data_dir / 'validation_v1.tsv', sep='\t', index=False)
print(len(result_array))
print(result)
print(result[True]+result[False])
print((100*result[True])/(result[True]+result[False]))

        