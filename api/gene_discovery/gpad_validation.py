'''
Author: Tahsin Hassan Rahit <kmtahsinhassan.rahit@ucalgary.ca>
Created: Thursday, June 10th 2021, 12:10:59 pm
-----
Copyright (c) 2021 Tahsin Hassan Rahit, MTG-lab, University of Calgary

You should have received a copy of the license along with this program.
'''

from time import sleep
from unittest import result
import pandas as pd
import pendulum
import logging

import plotly.express as px

from rich import print
from tqdm import tqdm
from api.gene_discovery.models import AssociationInformation, GeneEntry
from api.gene_discovery.settings import data_dir

from Bio import Entrez

Entrez.email = "tahsin.rahit@gmail.com"

# python -m api.gene_discovery.consistancy_validation

# 3862 


class Validation:
    
    def __init__(self) -> None:    
        self.ehrhart_df = pd.read_csv(data_dir / 'Gene-RD-Provenance_V2.1.txt', sep='\t').dropna(subset=["ENSID"]).fillna(0) # Ehrhart et al (2021)
        self.ehrhart_df['Disease OMIM ID'] = [int(row['Disease OMIM ID']) for idx, row in self.ehrhart_df.iterrows()]
        self.ehrhart_df['PMID Gene-disease'] = [int(row['PMID Gene-disease']) for idx, row in self.ehrhart_df.iterrows()]
        
        self.chong_df = pd.read_csv(data_dir / '2022-11-11.combinedOMIM.mentionsNGS.year.inheritance.txt', sep='\t') # Chong et al (2015)
        self.entries = AssociationInformation.objects(mapping_key__ne=2)
        # logging.debug(self.ehrhart_df)
        self.result = pd.DataFrame()    # To store validated results
        print(f"Total {len(self.entries)} confirmed associations will now be evaluated")
    
    def get_years(self):
        # entries = db.latest.find(query)
        i = 0
        result_arr = []
        total_entries = len(self.entries)
        result = {True: 0, False: 0, 'NA': 0, 'NOASSOC': 0}
        for entry in tqdm(self.entries, total=total_entries):
            gene_entry = GeneEntry.objects(mimNumber=entry['gene_mim_id']).first()
            
            # Detecting entry from chong 
            chong = False
            year = 0
            chong_rows = self.chong_df[(self.chong_df['origMIMnum']==entry['phenotype_mim']) & (self.chong_df['geneMIMnum']==entry['gene_mim_id'])].fillna(0)
            if len(chong_rows)>0:
                chong = int(chong_rows['yearDiscovered'].values[0])
                
            ensemble_ids = []
            if 'geneMap' in gene_entry and 'ensemblIDs' in gene_entry['geneMap']:
                # logging.debug(gene_entry['geneMap']['ensemblIDs'])
                ensemble_ids = gene_entry['geneMap']['ensemblIDs'].split(',')
            # logging.debug(ensemble_ids)
            ehrhart_rows = self.ehrhart_df[(self.ehrhart_df['ENSID'].isin(ensemble_ids)) & (self.ehrhart_df['Disease OMIM ID']==entry['phenotype_mim'])]
            # logging.debug(ehrhart_rows)
            
            ehrhart = False
            pmid = 'GPADUA'
            year = 0
            ehr_year = 'NA'
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
                        if row['PMID Gene-disease']:
                            handle = Entrez.esummary(db="pubmed", id=row['PMID Gene-disease'])
                            record = Entrez.read(handle)
                            handle.close()
                            ehr_year = record[0]["PubDate"]
                        result_arr.append([entry['gene_mim_id'], entry['phenotype_mim'], pmid, year, row['PMID Gene-disease'], ehr_year, chong])
                        ehrhart = True
                        break
            elif ehrhart == 'NOASSOC':
                # Evidence not available on GPAD
                result_arr.append([entry['gene_mim_id'], entry['phenotype_mim'], pmid, year, len(ehrhart_rows.index) > 0, ehr_year, chong])
            else:
                # Evidence not available in Ehrhart
                result_arr.append([entry['gene_mim_id'], entry['phenotype_mim'], pmid, year, 'NA', ehr_year, chong])
                ehrhart = 'NA'
            if ehrhart == False:
                # PMID does not match with ehrhart
                result_arr.append([entry['gene_mim_id'], entry['phenotype_mim'], pmid, year, False, ehr_year, chong])
            
            result[ehrhart] += 1
            sleep(0.1)  # Respecting Entrez API request threshold
        # logging.debug(result_arr)
        self.result = pd.DataFrame(result_arr, columns=['gene', 'pheno', 'gpad_pmid', 'gpad_year', 'ehrhart_pmid', 'ehrhart_year', 'chong_year'])
    
    
    def __match(self, row, col_a, col_b):
        # logging.debug(col_a)
        # return True
        if row[col_a] == 0:
            return col_a + '_ua'
        elif row[col_b] == 0:
            return col_b + '_ua'
        # logging.debug(row[col_a] == row[col_b])
        return row[col_a] == row[col_b]
    
    
    def evaluate_match(self):
        """Compare the years and add match column to the result
        """
        # logging.debug(self.result.apply(self.__match, axis=0, col_a='gpad_year', col_b='ehrhart_year'))
        self.result['gpad_x_ehrhart'] = self.result.apply(self.__match, axis=1, col_a='gpad_year', col_b='ehrhart_year')
        self.result['gpad_x_chong'] = self.result.apply(self.__match, axis=1, col_a='gpad_year', col_b='chong_year')
        self.result['ehrhart_x_chong'] = self.result.apply(self.__match, axis=1, col_a='ehrhart_year', col_b='chong_year')       
        
    
    def save(self, as_excel=False):
        """Save the evaluation as an excel file
        """
        if as_excel:
            self.result.to_excel(data_dir / f"validation_{pendulum.now()}.xlsx", sheet_name="GPAD", index=False)
        else:
            self.result.to_csv(data_dir / f"validation_{pendulum.now()}.tsv", sep='\t', index=False)
        # print(result)
        # print(f"Total Result: {len(self.result)}")        
        # print(result[True]+result[False])
        # print((100*result[True])/(result[True]+result[False]))

    def plot(self):
        for col in ['gpad_x_ehrhart', 'gpad_x_chong', 'ehrhart_x_chong']:
            pie_df = self.result.groupby([col])[col].count()
            logging.debug(pie_df)
            fig = px.pie(pie_df, values=col, names=col, title=col)
            fig.write_image(data_dir/f"{col}_{pendulum.now()}.png")