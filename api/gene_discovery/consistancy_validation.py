'''
Author: Tahsin Hassan Rahit <kmtahsinhassan.rahit@ucalgary.ca>
Created: Thursday, June 10th 2021, 12:10:59 pm
-----
Copyright (c) 2021 Tahsin Hassan Rahit, MTG-lab, University of Calgary

You should have received a copy of the license along with this program.
'''

import pandas as pd
import numpy as np
from pathlib import Path
import pprint
from tqdm import tqdm
from api.gene_discovery.settings import db, project_dir

# python -m api.gene_discovery.consistancy_validation

# 3862 


df = pd.read_csv(project_dir / '../data/Gene-RD-Provenance_V2.txt', sep='\t').dropna(subset=["ENSID"])

df['GPAD_pmid'] = 0
result = {True: 0, False: 0, 'NA': 0}
for idx, row in tqdm(df.iterrows(), total=df.shape[0]):
    if row['ENSID']:
        query = {'$text': {'$search': str(row['ENSID'])}}
        if db.gene_entry.count_documents(query):
            entry = db.gene_entry.find_one(query)
            query = {'$and': [{'gene_mim_id': entry['mimNumber']}, {'phenotype_mim': int(row['Disease OMIM ID'])}]} # {'gene_mim_id': entry['mimNumber']}
            # print(query)
            if db.earliest_phenotype_association.count_documents(query):
                # print('asd')
                entries = db.earliest_phenotype_association.find(query)
                for entry in entries:
                    if 'earliest_phenotype_association' in entry and 'pmid' in entry['earliest_phenotype_association']:
                        pmid = entry['earliest_phenotype_association']['pmid']
                        df.loc[idx,'GPAD_pmid'] = pmid
                        if not np.isnan(row['PMID Gene-disease']):
                            result[int(row['PMID Gene-disease']) == pmid] += 1
                        elif 'earliest_phenotype_association' not in entry:
                            result[True] += 1
                        else:
                            result[False] += 1
                    else:
                        result['NA'] += 1
                    # print(f"{int(row['PMID Gene-disease']) == pmid} : ({entry['gene_mim_id']} {entry['phenotype_mim']}) => {row['PMID Gene-disease']} {pmid}")
df.to_csv(project_dir / '../data/Gene-RD-Provenance_V2_comparison2.tsv', sep='\t', index=False)
print(result)
print(result[True]+result[False])
print((100*result[True])/(result[True]+result[False]))