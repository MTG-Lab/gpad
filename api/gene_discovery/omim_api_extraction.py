
'''
Author: Tahsin Hassan Rahit <kmtahsinhassan.rahit@ucalgary.ca>
Created: Friday, March 5th 2021, 11:04:37 am
-----
Copyright (c) 2021 Tahsin Hassan Rahit, MTG-lab, University of Calgary

You should have received a copy of the license along with this program.
'''

import datetime
import logging
import math

import pendulum
import requests
from rich import print
from tqdm import tqdm, trange
from mongoengine.queryset.visitor import Q

from .models import *
from .settings import *




class OmimApiAdapter:
    
    limit = 100
    # params = {
    #     'has_update': {
    #         'search': 'number:'+','.join(mims_to_check.keys()),
    #         'sort': 'score+desc',
    #         'start': 0,
    #         'limit': limit,
    #         'include': 'dates',
    #         'format': 'json'
    #     }
    # }




def omim_request(handle: str, params: dict):
    """Send OMIM API request

    Args:
        handle (str): _description_
        params (dict): _description_
    """
    try: 
        return requests.get(
            'https://api.omim.org/api/'+handle,
            params=params,
            headers={'ApiKey': OMIM_API_KEY},
        )
    except:
        print(f"[red]Daily OMIM request limit exceed. Please  rerun the command tommorrow and it will safely resume.[/red]")
    
    return False


def has_update(mims_to_check):
    """Check OMIM database if there is a update for an entry

    Args:
        mims_to_check (list[GeneEntry]): List of GeneEntry objects

    Returns:
        list: mim ids that have updates
    """
    limit = 100
    # mims = [str(mim) for mim in mims_to_check.keys()]
    params={
        'search': 'number:'+','.join(mims_to_check.keys()),
        'sort': 'score+desc',
        'start': 0,
        'limit': limit,
        'include': 'dates',
        'format': 'json'
    }
    # Search through OMIM API
    response = omim_request('entry/search', params)
    if response:
        checked = []
        logging.debug(response.json())
        for entry in response.json()['omim']['searchResponse']['entryList']:
            mim = str(entry['entry']['mimNumber'])
            if mim in mims_to_check.keys():
                origin = pendulum.instance(
                    datetime.datetime.strptime(
                        entry['entry']['dateUpdated'], '%a, %d %b %Y %H:%M:%S %Z'))
                if mims_to_check[mim][0].omim_entry_fetched:
                    local = pendulum.instance(mims_to_check[mim][0].omim_entry_fetched)
                    mims_to_check[mim][1] = origin > local
                else:
                    mims_to_check[mim][1] = False
            checked.append(mim)
        logging.debug(f"Checked {len(checked)} of {len(mims_to_check.keys())}")
    return mims_to_check


def what_to_update():
    limit = 5
    mims_to_check = {}
    mims_to_fetch = []
    for assoc in tqdm(AssociationInformation.objects, colour='#999999', desc="Checking Updates"):
        if assoc.gene_entry_fetched:
            mims_to_check[str(assoc.gene_mimNumber)] = [assoc, False]
        if assoc.pheno_entry_fetched:
            mims_to_check[str(assoc.pheno_mimNumber)] = [assoc, False]
            # WIP change to assoc dict
            # if len(mims_to_check.keys()+1) > limit:
            #     checked_mims = has_update(mims_to_check)
            #     for k, cm in checked_mims.items():
            #         logging.info(f"{cm[0].mimNumber}: {cm[1]}")
            #         if cm[1]:
            #             mims_to_fetch.append(cm[0].mimNumber)
            #             for p in cm[0].phenotypes:
            #                 mims_to_fetch.append(p.mim_number)
            #     mims_to_check = {}
        else:
            mims_to_fetch.append(assoc.pheno_mimNumber)
            if 'phenotypes' in assoc:
                for p in assoc.phenotypes:
                    mims_to_fetch.append(p.mim_number)
    return mims_to_fetch



def get_geneMaps():
    """ Getting the gene mim ids from OMIM api using date range

    Args:
        date_from ([type]): start date. Use 0000 to start from earliest. See doc: 
        date_to ([type]): End date. See doc: 
    """
    limit = 100
    params={
        'search': 'phenotype_exists:true',
        'start': 0,
        'limit': limit,
        'format': 'json'
    }
    # Search through OMIM API
    response = omim_request('geneMap/search', params)
    
    # Iterating though results and paging
    all_mims = []
    more_page = True
    
    if response:
        total_result = response.json()['omim']['searchResponse']['totalResults']
        pbar = tqdm(total=total_result, colour="green", desc="Getting Associations")
        while more_page:
            _entries = response.json()['omim']['searchResponse']['geneMapList']
            # Persist in DB
            for gene in _entries:
                if 'phenotypeMapList' in gene['geneMap'] and len(gene['geneMap']['phenotypeMapList']):
                    all_mims.append(int(gene['geneMap']['mimNumber']))
                    for pheno in gene['geneMap']['phenotypeMapList']:
                        if 'phenotypeMimNumber' in pheno['phenotypeMap']:
                            # logging.debug(f"{gene['geneMap']['mimNumber']} - {pheno['phenotypeMap']['phenotypeMimNumber']}")
                            assoc = AssociationInformation.objects.filter(
                                (Q(gene_mimNumber=gene['geneMap']['mimNumber']) and Q(pheno_mimNumber=pheno['phenotypeMap']['phenotypeMimNumber']))).first()
                            if assoc  == None:
                                assoc = AssociationInformation()
                                assoc["gene_mimNumber"] = gene['geneMap']['mimNumber']
                                assoc['pheno_mimNumber'] = pheno['phenotypeMap']['phenotypeMimNumber']
                                assoc.gpad_created = pendulum.now()                            
                            # ai['gene_prefix'] = gene_entry.prefix
                            if 'geneSymbols' in gene['geneMap']:
                                assoc["gene_symbols"] = gene['geneMap']['geneSymbols']
                            if 'geneName' in gene['geneMap']:
                                assoc["gene_name"] = gene['geneMap']['geneName']
                            
                            if 'phenotype' in pheno['phenotypeMap']:
                                assoc["phenotype"] = pheno['phenotypeMap']['phenotype']
                            if 'phenotypeMappingKey' in pheno['phenotypeMap']:
                                assoc["mapping_key"] = pheno['phenotypeMap']['phenotypeMappingKey']
                            if 'phenotypeInheritance' in pheno['phenotypeMap']:
                                assoc["inheritance"] = pheno['phenotypeMap']['phenotypeInheritance']
                            assoc.gpad_updated = pendulum.now()
                            # logging.debug(assoc)
                            assoc.save()
                            all_mims.append(int(pheno['phenotypeMap']['phenotypeMimNumber']))
                            # phenos.append(pheno)
            # Next page
            end_idx = response.json()['omim']['searchResponse']['endIndex']
            start_idx = end_idx + 1
            more_page = total_result > end_idx + 1
            # logging.debug(response.json())
            logging.info(f"{total_result} < {end_idx + 1} = {more_page}")
            pbar.update(limit)
            params={
                'search': 'phenotype_exists:true',
                'start': start_idx,
                'limit': limit,
                'format': 'json'
            }
            response = omim_request('geneMap/search', params)
    return all_mims


def get_gene_ids(date_from, date_to):
    """ Getting the gene mim ids from OMIM api using date range

    Args:
        date_from ([type]): start date. Use 0000 to start from earliest. See doc: 
        date_to ([type]): End date. See doc: 
    """
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
    print(f"Total {len(all_gene_ids)} entries to extract. {len(mim_ids_already_exists)} are already exist in the DB.")
    return genes_to_extract

def extract_gene_info(genes_to_extract):
    """Extract text and related information from OMIM API

    Args:
        genes_to_extract (List[int]): List of OMIM MIM IDs to extract
    """
    gene_count = len(genes_to_extract)
    extracted = []
    for i in trange(int(math.ceil(gene_count/OMIM_RESPONSE_LIMIT)), desc='Getting Text from OMIM API'):
        # logging.info(f"Page {i}")
        omim_genes = genes_to_extract[i*OMIM_RESPONSE_LIMIT:(i+1)*OMIM_RESPONSE_LIMIT] 
        response = requests.get(
            'https://api.omim.org/api/entry',
            params={
                'mimNumber': ','.join(str(m) for m in omim_genes),
                'include': 'text,allelicVariantList,geneMap,phenotypeMap,referenceList,externalLinks,dates,editHistory,creationDate',
                'format': 'json'
            },
            headers={'ApiKey': OMIM_API_KEY},
        )
        if response:
            response_entries = response.json()['omim']['entryList']
            for r in response_entries:
                entry = GeneEntry.objects(
                    mimNumber=r['entry']['mimNumber']).first()
                if entry == None:
                    entry = GeneEntry()
                    entry.mtgCreated = datetime.datetime.now()                
                    entry.mimNumber = r['entry']['mimNumber']
                entry.status = r['entry']['status']
                entry.titles = r['entry']['titles']
                entry.creationDate = r['entry']['creationDate']
                entry.editHistory = r['entry']['editHistory']
                entry.epochCreated = r['entry']['epochCreated']
                entry.dateCreated = r['entry']['dateCreated']
                entry.epochUpdated = r['entry']['epochUpdated']
                entry.dateUpdated = r['entry']['dateUpdated']
                entry.mtgUpdated = datetime.datetime.now()
                if 'prefix' in r['entry']:
                    entry.prefix = r['entry']['prefix']
                if 'geneMap' in r['entry']:
                    entry.geneMap = r['entry']['geneMap']
                if 'textSectionList' in r['entry']:
                    entry.textSectionList = r['entry']['textSectionList']
                if 'allelicVariantList' in r['entry']:
                    entry.allelicVariantList = r['entry']['allelicVariantList']
                if 'referenceList' in r['entry']:
                    entry.referenceList = r['entry']['referenceList']
                if 'externalLinks' in r['entry']:
                    entry.externalLinks = r['entry']['externalLinks']
                logging.debug(f"Saving {entry.mimNumber}")
                entry.save()
                
                assoc = AssociationInformation.objects.filter(
                    (Q(gene_mimNumber=r['entry']['mimNumber']) or Q(pheno_mimNumber=r['entry']['mimNumber']))).first()
                if assoc:
                    if assoc.gene_mimNumber == r['entry']['mimNumber']:
                        assoc.gene_entry_fetched = pendulum.now()
                    elif assoc.gene_mimNumber == r['entry']['mimNumber']:
                        assoc.pheno_entry_fetched = pendulum.now()                        
                    assoc.gpad_updated = pendulum.now()
                    assoc.save()
                
                extracted.append(int(r['entry']['mimNumber']))
        else:
            return extracted

