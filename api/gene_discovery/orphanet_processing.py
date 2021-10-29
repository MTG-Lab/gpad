'''
Author: Tahsin Hassan Rahit <kmtahsinhassan.rahit@ucalgary.ca>
Created: Thursday, August 26th 2021, 4:19:17 pm
-----
Copyright (c) 2021 Tahsin Hassan Rahit, MTG-lab, University of Calgary

You should have received a copy of the license along with this program.
'''
# python -m api.gene_discovery.orphanet_processing

import time
import math
from tqdm import tqdm
import xml.etree.ElementTree as ET
import pandas as pd
import requests
from .settings import *

# df = pd.read_csv(data_dir/'orphanet_processed.csv', converters={"assoc_source": lambda x: x.strip("[]").split(", ")})
# # pmid_df = pd.read_csv(data_dir/'PMC-ids.csv.gz')
# # print(pmid_df.columns)
# for index, row in df.iterrows():
#     if not math.isnan(row['omim_pmid']) and row['assoc_source']:
#         # omim_pub = pmid_df[pmid_df['PMID'] == row['omim_pmid']]
#         # print(row['assoc_source'])
#         # for pmid in row['assoc_source']:
#         #     orpha_source = pmid_df[pmid_df['PMID'] == pmid]
#         # print(omim_pub['Year'], orpha_source['Year'])
#         orpha_sources = [p.strip("'") for p in row['assoc_source']]
#         pmids_to_extract = [format(row['omim_pmid'], '.0f')] + orpha_sources
#         print(pmids_to_extract)
#         response = requests.get(
#             'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi',
#             params={
#                 'id': ','.join(pmid for pmid in pmids_to_extract),
#                 'db': 'pubmed',
#                 'retmode': 'xml',
#                 'rettype': 'pubmed',
#                 'tool': 'gene_discovery_analyzer'
#             },
#             headers={'api_key': NCBI_API_KEY},
#         )
#         years = []
#         if response.content:
#             pubmed_articles = ET.fromstring(response.content)
#             for pubmed_article in pubmed_articles.iter('PubmedArticle'):
#                 pmid = pubmed_article.find('MedlineCitation//PMID').text
#                 pmid_year = pubmed_article.find('MedlineCitation//PubDate/Year').text
#                 years.append(pmid_year)
#                 # if format(row['omim_pmid'], '.0f') == pmid:
#                 #     print(f"OMIM says {pmid_year}")
#                 # else:
#                 #     print(pmid_year)
#         print(years)
#                 # abstract_dom = pubmed_article.find('MedlineCitation//Abstract//AbstractText')
#                 # ncbi_entry = NCBIEntry.objects(pmid=pmid).only('pmid').first()
#                 # if not ncbi_entry and pmid and abstract_dom:
#                 #     ncbi_entry = NCBIEntry()
#                 #     ncbi_entry['pmid'] = pmid
#                 #     ncbi_entry['abstract'] = abstract_dom.text
#                 #     ncbi_entry.save()
#         time.sleep(0.5)   # NCBI allows 3 (without API key) and 10 (with API key) requests per seconds.


def get_pmid_years(pmids_to_extract):
    years = []
    response = requests.get(
        'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi',
        params={
            'id': ','.join(pmid for pmid in pmids_to_extract),
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
            try:
                pmid_year = pubmed_article.find('./MedlineCitation//PubDate/Year').text
                years.append(pmid_year)
            except:
                pmid = pubmed_article.find('./MedlineCitation//PMID').text
                logging.warning(f"Error extracting year info for PMID {pmid}")
    time.sleep(0.5)   # NCBI allows 3 (without API key) and 10 (with API key) requests per seconds.
    return years


dis_root = ET.parse(data_dir/'en_product1.xml')
gda_root = ET.parse(data_dir/'en_product6.xml')
epi_root = ET.parse(data_dir/'en_product9_prev.xml')

orpha_omim = {}
for disorder in dis_root.findall('./DisorderList/'):
    orpha = disorder.find("./OrphaCode").text
    for ref in disorder.findall(".//ExternalReferenceList/"):
            if ref.find("./Source[.='OMIM']") is not None and ref.find("./Source[.='OMIM']").text == 'OMIM':
                omim = ref.find("./Reference").text
    if orpha in orpha_omim:
        orpha_omim[orpha].append(omim)
    else:
        orpha_omim[orpha] = [omim]


orpha_epi = {}
for disorder in epi_root.findall('./DisorderList/'):
    orpha = disorder.find("./OrphaCode").text
    prevalance = None
    for ref in disorder.findall(".//PrevalenceList/"):
        if ref.find("./PrevalenceGeographic/Name[.='Worldwide']")  is not None \
            and ref.find("./PrevalenceValidationStatus/Name[.='Validated']") is not None \
            and ref.find("./PrevalenceClass/Name") is not None:
            prevalance = ref.find("./PrevalenceClass/Name").text
    orpha_epi[orpha] = prevalance

gda_processed = []
# c = 0
for disorder in tqdm(gda_root.findall('./DisorderList/')):
    orpha = disorder.find("./OrphaCode").text
    for gda in disorder.findall('./DisorderGeneAssociationList/'):
        type = gda.find("./DisorderGeneAssociationType/Name").text
        status = gda.find("./DisorderGeneAssociationStatus/Name").text
        source = gda.find("./SourceOfValidation").text
        source_years = []
        if source:
            source = source.replace('[PMID]','').split('_')
            source_years += get_pmid_years(source)
            # print(source_years)
        # Epidemiology
        for ref in gda.findall(".//ExternalReferenceList/"):
            if ref.find("./Source[.='OMIM']") is not None and ref.find("./Source[.='OMIM']").text == 'OMIM':
                omim_pheno_id = None
                epi_data = None
                omim_pmid = None
                omim_year = None
                omim_gene_id = ref.find("./Reference").text
                if orpha in orpha_omim:
                    for mim_id in orpha_omim[orpha]:
                        omim_pheno_id = mim_id
                        if orpha in orpha_epi:
                            epi_data = orpha_epi[orpha]

                        query = {
                            '$and': [
                                {'gene_mim_id': int(omim_gene_id)},
                                {'phenotype_mim': int(omim_pheno_id)}
                            ]
                        }
                        if db.latest.count_documents(query):
                            # c += 1
                            omim_assoc = db.latest.find_one(query)
                            if 'earliest_phenotype_association' in omim_assoc and 'pmid' in omim_assoc['earliest_phenotype_association']:
                                omim_pmid = format(omim_assoc['earliest_phenotype_association']['pmid'], '.0f')
                                omim_year = omim_assoc['earliest_phenotype_association']['year']
                        gda_processed.append([orpha, omim_pheno_id, omim_gene_id, epi_data, source, source_years, omim_pmid, omim_year, type, status])
# print(c)
df = pd.DataFrame(gda_processed, columns=['orphanet_disease_id', 'omim_phenotype_id', 'omim_gene_id', 'disease_prevalance', 'assoc_source', 'source_years', 'omim_pmid', 'omim_year', 'assoc_type', 'assoc_status'])
df.to_csv(data_dir/'orphanet_processed.csv', index=False)

