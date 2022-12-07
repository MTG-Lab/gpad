'''
Author: Tahsin Hassan Rahit <kmtahsinhassan.rahit@ucalgary.ca>
Created: Thursday, June 10th 2021, 12:10:59 pm
-----
Copyright (c) 2021 Tahsin Hassan Rahit, MTG-lab, University of Calgary

You should have received a copy of the license along with this program.

This script validate GPAD's result by comparing with Chong et al. (2015) [PMID:26166479]
'''

from unittest import result
import pandas as pd
import numpy as np
from pathlib import Path
import pprint
from tqdm import tqdm
from api.gene_discovery.settings import db, data_dir

# python -m api.gene_discovery.gpad_validation_chong.py

# 3862 


df = pd.read_csv(data_dir / '2022-11-11.combinedOMIM.mentionsNGS.year.inheritance.txt', sep='\t')
query = {'mapping_key': {'$ne': 2}}
entries = db.latest.find(query)
df.fillna(0)
# df['origMIMnum'] = [int(row['origMIMnum']) for idx, row in df.iterrows()]
# df['geneMIMnum'] = [int(row['geneMIMnum']) for idx, row in df.iterrows()]

result_array = []
total_entries = db.latest.count_documents(query)
i = 0

result = {True: 0, False: 0, 'NA': 0, 'NOASSOC': 0}
for entry in tqdm(entries, total=total_entries):
    chong = False
    year = 0
    chong_rows = df[(df['origMIMnum']==entry['phenotype_mim']) & (df['geneMIMnum']==entry['gene_mim_id'])].fillna(0)
    if len(chong_rows)>0:
        chong = int(chong_rows['yearDiscovered'].values[0])
    
    if 'earliest_phenotype_association' in entry and 'year' in entry['earliest_phenotype_association']:
        year = entry['earliest_phenotype_association']['year']
    else:
        year = 0 # No evidence available on GPAD
    
    result_array.append([entry['gene_mim_id'], entry['phenotype_mim'], year, chong])
    
    # if year != 'NA' and len(chong_rows.index):
    #     # Evidence available in chong            
    #     for idx, row in chong_rows.iterrows():
    #         if row['yearDiscovered'] == year:
    #             # match year
    #             result_array.append([entry['gene_mim_id'], entry['phenotype_mim'], year, row['yearDiscovered']])
    #             chong = True
    #             break
    # elif year == 'NA':
    #     # Evidence not available on GPAD
    #     result_array.append([entry['gene_mim_id'], entry['phenotype_mim'], year, len(chong_rows.index) > 0])
    # else:
    #     # Evidence not available in Chong
    #     result_array.append([entry['gene_mim_id'], entry['phenotype_mim'], year, 'NA'])
    #     chong = 'NA'
    # if chong == False:
    #     # PMID does not match with Chong
    #     result_array.append([entry['gene_mim_id'], entry['phenotype_mim'], year, False])
    result[year==chong] += 1
        
result_df = pd.DataFrame(result_array)
result_df.to_csv(data_dir / 'validation_chong_v1.2.tsv', sep='\t', index=False)
print(len(result_array))
print(result)
print(result[True]+result[False])
print((100*result[True])/(result[True]+result[False]))

        