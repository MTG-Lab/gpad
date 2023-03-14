'''
Author: Tahsin Hassan Rahit <kmtahsinhassan.rahit@ucalgary.ca>
Created: Thursday, June 10th 2021, 12:10:59 pm
-----
Copyright (c) 2021 Tahsin Hassan Rahit, MTG-lab, University of Calgary

You should have received a copy of the license along with this program.
'''

import re
from time import sleep
from unittest import result
import pandas as pd
import numpy as np
import pendulum
import logging

import plotly.express as px

from rich import print
from tqdm import tqdm
from api.gene_discovery.models import AssociationInformation, GeneEntry, PubmedEntry
from api.gene_discovery.settings import data_dir

from Bio import Entrez

Entrez.email = "tahsin.rahit@gmail.com"

# python -m api.gene_discovery.consistancy_validation

# 3862 


class Validation:
    
    year_regex = r"\d{4}"
    
    def __init__(self) -> None:    
        self.ehrhart_df = pd.read_csv(data_dir / 'Gene-RD-Provenance_V2.1.txt', sep='\t').dropna(subset=["ENSID"]).fillna(0) # Ehrhart et al (2021)
        self.ehrhart_df['Disease OMIM ID'] = [int(row['Disease OMIM ID']) for idx, row in self.ehrhart_df.iterrows()]
        self.ehrhart_df['PMID Gene-disease'] = [int(row['PMID Gene-disease']) for idx, row in self.ehrhart_df.iterrows()]
        self.ehrhart_df['year'] = self.ehrhart_df.apply(self.__add_year_from_pubmed, axis=1)
        
        self.chong_df = pd.read_csv(data_dir / '2022-11-11.combinedOMIM.mentionsNGS.year.inheritance.txt', sep='\t') # Chong et al (2015)
        self.entries = AssociationInformation.objects   #(mapping_key=2)
        # logging.debug(self.ehrhart_df)
        self.result = pd.DataFrame()    # To store validated results
        print(f"Total {len(self.entries)} confirmed associations will now be evaluated")
        
    def __add_year_from_pubmed(self, row):
        """Add year column to Ehrhart's dataframe

        Args:
            row (_type_): PMID with column name `PMID Gene-disease` found in Ehrhart et al. (2015)

        Returns:
            _type_: year
        """
        if row['PMID Gene-disease']:
            pe = PubmedEntry.objects(pmid=row['PMID Gene-disease']).first()
            if pe == None:
                logging.info(f"Sending Entrez request for PMID: {row['PMID Gene-disease']}")
                pe = PubmedEntry()
                handle = Entrez.esummary(db="pubmed", id=row['PMID Gene-disease'])
                record = Entrez.read(handle)
                handle.close()
                pe.pmid = row['PMID Gene-disease']
                pe.pub_date = record[0]["PubDate"]
                yr_match = re.match(self.year_regex, record[0]["PubDate"])
                pe.pub_year = yr_match.group()
                pe.save()
            return pe.pub_year
        return None
    
    def __add_chong(self, row):
        chong = None
        chong_rows = self.chong_df[(self.chong_df['origMIMnum']==row['pheno_mimNumber']) & (self.chong_df['geneMIMnum']==row['gene_mimNumber'])].fillna(0)
        if len(chong_rows)>0:
            chong = int(chong_rows['yearDiscovered'].values[0])
        
    def combine(self):
        # entries = db.latest.find(query)
        i = 0
        result_arr = []
        total_entries = len(self.entries)
        result = {True: 0, False: 0, 'NA': 0, 'NOASSOC': 0}
        chong_col_num = len(self.chong_df.columns)
        for entry in tqdm(self.entries, total=total_entries, colour='blue'):
            # if entry.evidence:
            gene_entry = GeneEntry.objects(mimNumber=entry['gene_mimNumber']).first()
            
            pmid = False
            year = False
            ehrhart = []
            ehr_year = []
            chong = False
            source = False
            
            # Detecting entry from chong             
            chong_rows = self.chong_df[(self.chong_df['origMIMnum']==entry['pheno_mimNumber']) & (self.chong_df['geneMIMnum']==entry['gene_mimNumber'])].fillna(0)
            chong_idx = -1
            if len(chong_rows)>0:
                chong = int(chong_rows['yearDiscovered'].values[0])
                # chong_rows = np.array(chong_rows.values[0])
                chong_idx = int(chong_rows.index[0])
            # else:
                # chong_rows = np.zeros((1,chong_col_num))
                
            ensemble_ids = []
            if gene_entry and 'geneMap' in gene_entry and 'ensemblIDs' in gene_entry['geneMap']:
                # logging.debug(gene_entry['geneMap']['ensemblIDs'])
                ensemble_ids = gene_entry['geneMap']['ensemblIDs'].split(',')
            # logging.debug(ensemble_ids)
            ehrhart_rows = self.ehrhart_df[(self.ehrhart_df['ENSID'].isin(ensemble_ids)) & (self.ehrhart_df['Disease OMIM ID']==entry['pheno_mimNumber'])]
            # logging.debug(ehrhart_rows)
            
            if 'evidence' in entry and 'publication_evidence' in entry['evidence']:
                year = entry['evidence']['publication_evidence']['year']
                source = entry.evidence.section_title
                if  'pmid' in  entry['evidence']['publication_evidence']:
                    pmid =  entry['evidence']['publication_evidence']['pmid']
                else:
                    pmid = 'NA'
            
            ehrhart = ehrhart_rows[ehrhart_rows['PMID Gene-disease']==pmid] # match pmid first
            if ehrhart.empty:   # if not then match year
                ehrhart = ehrhart_rows[ehrhart_rows['year']==year]
            if ehrhart.empty:   # if still empty then match chong
                ehrhart = ehrhart_rows[ehrhart_rows['year']==chong]
            
            if ehrhart.shape[0] > 0:
                ehr_year = ehrhart['year'].values[0]
                # ehr_year = ehrhart['PMID Gene-disease'].values[0]
                result_arr.append([
                    entry['gene_prefix'], entry['gene_mimNumber'], 
                    entry['pheno_prefix'], entry['pheno_mimNumber'], 
                    entry['mapping_key'], entry['phenotype'], 
                    entry['gene_mimNumber'], entry['pheno_mimNumber'], 
                    source, pmid, year, ehrhart['PMID Gene-disease'].values[0], 
                    ehr_year, chong, chong_idx])
            else:
                result_arr.append([
                    entry['gene_prefix'], entry['gene_mimNumber'], 
                    entry['pheno_prefix'], entry['pheno_mimNumber'], 
                    entry['mapping_key'], entry['phenotype'], 
                    entry['gene_mimNumber'], entry['pheno_mimNumber'], 
                    source, pmid, year, False, False, chong, chong_idx])

        # logging.debug(result_arr)
        self.result = pd.DataFrame(result_arr, columns=[
                        'gene_prefix', 'gene_mimNumber',
                        'pheno_prefix', 'pheno_mimNumber',
                        'mapping_key', 'phenotype',
                        'gene_mimNumber', 'pheno_mimNumber', 
                        'source_section', 'gpad_pmid', 'gpad_year', 
                        'ehrhart_pmid', 'ehrhart_year', 'chong_year', 'chong_idx'])
        self.result.fillna(False, inplace=True)
        self.result = self.result.merge(self.chong_df.fillna(False), how='outer', left_on=['chong_idx'], right_index=True)
    
    
    def get_years(self):
        # entries = db.latest.find(query)
        i = 0
        result_arr = []
        total_entries = len(self.entries)
        result = {True: 0, False: 0, 'NA': 0, 'NOASSOC': 0}
        chong_col_num = len(self.chong_df.columns)
        for entry in tqdm(self.entries, total=total_entries, colour='blue'):
            if entry.evidence:
                gene_entry = GeneEntry.objects(mimNumber=entry['gene_mimNumber']).first()
                
                pmid = False
                year = False
                ehrhart = []
                ehr_year = []
                chong = False
                source = False
                
                # Detecting entry from chong             
                chong_rows = self.chong_df[(self.chong_df['origMIMnum']==entry['pheno_mimNumber']) & (self.chong_df['geneMIMnum']==entry['gene_mimNumber'])].fillna(0)
                chong_idx = -1
                if len(chong_rows)>0:
                    chong = int(chong_rows['yearDiscovered'].values[0])
                    # chong_rows = np.array(chong_rows.values[0])
                    chong_idx = int(chong_rows.index[0])
                # else:
                    # chong_rows = np.zeros((1,chong_col_num))
                    
                ensemble_ids = []
                if gene_entry and 'geneMap' in gene_entry and 'ensemblIDs' in gene_entry['geneMap']:
                    # logging.debug(gene_entry['geneMap']['ensemblIDs'])
                    ensemble_ids = gene_entry['geneMap']['ensemblIDs'].split(',')
                # logging.debug(ensemble_ids)
                ehrhart_rows = self.ehrhart_df[(self.ehrhart_df['ENSID'].isin(ensemble_ids)) & (self.ehrhart_df['Disease OMIM ID']==entry['pheno_mimNumber'])]
                # logging.debug(ehrhart_rows)
                
                if 'evidence' in entry and 'publication_evidence' in entry['evidence']:
                    year = entry['evidence']['publication_evidence']['year']
                    source = entry.evidence.section_title
                    if  'pmid' in  entry['evidence']['publication_evidence']:
                        pmid =  entry['evidence']['publication_evidence']['pmid']
                    else:
                        pmid = 'NA'
                
                ehrhart = ehrhart_rows[ehrhart_rows['PMID Gene-disease']==pmid] # match pmid first
                if ehrhart.empty:   # if not then match year
                    ehrhart = ehrhart_rows[ehrhart_rows['year']==year]
                if ehrhart.empty:   # if still empty then match chong
                    ehrhart = ehrhart_rows[ehrhart_rows['year']==chong]
                
                if ehrhart.shape[0] > 0:
                    ehr_year = ehrhart['year'].values[0]
                    # ehr_year = ehrhart['PMID Gene-disease'].values[0]
                    result_arr.append([
                        entry['gene_prefix'], entry['gene_mimNumber'], 
                        entry['pheno_prefix'], entry['pheno_mimNumber'], 
                        entry['mapping_key'], entry['phenotype'], 
                        entry['gene_mimNumber'], entry['pheno_mimNumber'], 
                        source, pmid, year, ehrhart['PMID Gene-disease'].values[0], 
                        ehr_year, chong, chong_idx])
                elif ehrhart_rows.shape[0] > 0:
                    ehr_year = ehrhart_rows['year'].values[0]
                    result_arr.append([
                        entry['gene_prefix'], entry['gene_mimNumber'], 
                        entry['pheno_prefix'], entry['pheno_mimNumber'], 
                        entry['mapping_key'], entry['phenotype'], 
                        entry['gene_mimNumber'], entry['pheno_mimNumber'], 
                        source, pmid, year, ehrhart_rows['PMID Gene-disease'].values[0], ehr_year, chong, chong_idx])
                else:
                    result_arr.append([
                        entry['gene_prefix'], entry['gene_mimNumber'], 
                        entry['pheno_prefix'], entry['pheno_mimNumber'], 
                        entry['mapping_key'], entry['phenotype'], 
                        entry['gene_mimNumber'], entry['pheno_mimNumber'], 
                        source, pmid, year, False, False, chong, chong_idx])

        # logging.debug(result_arr)
        self.result = pd.DataFrame(result_arr, columns=[
                        'gene_prefix', 'gene_mimNumber',
                        'pheno_prefix', 'pheno_mimNumber',
                        'mapping_key', 'phenotype',
                        'gene_mimNumber', 'pheno_mimNumber', 
                        'source_section', 'gpad_pmid', 'gpad_year', 
                        'ehrhart_pmid', 'ehrhart_year', 'chong_year', 'chong_idx'])
        self.result.fillna(False, inplace=True)
        self.result = self.result.merge(self.chong_df.fillna(False), how='outer', left_on=['chong_idx'], right_index=True)
    
    
    def __match(self, row, col_a, col_b):
        # logging.debug(col_a)
        # return True
        row.fillna(False, inplace=True)
        if row[col_a] is False or row[col_a]==None:
            return col_a + '_ua'
        elif row[col_b] is False or row[col_b]==None:
            return col_b + '_ua'
        # logging.debug(row[col_a] == row[col_b])
        # if row[col_a]==pd.NA or row[col_b]==pd.NA:
        #     return 'NA'
        return int(row[col_a]) == int(row[col_b])
    
    
    def evaluate_match(self):
        """Compare the years and add match column to the result
        """
        # logging.debug(self.result.apply(self.__match, axis=0, col_a='gpad_year', col_b='ehrhart_year'))
        self.result['gpad_x_ehrhart'] = self.result.apply(self.__match, axis=1, col_a='gpad_year', col_b='ehrhart_year')
        self.result['gpad_x_chong'] = self.result.apply(self.__match, axis=1, col_a='gpad_year', col_b='chong_year')
        self.result['ehrhart_x_chong'] = self.result.apply(self.__match, axis=1, col_a='ehrhart_year', col_b='chong_year')       

    # def 
    
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