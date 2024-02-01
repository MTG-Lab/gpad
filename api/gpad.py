'''
Author: Tahsin Hassan Rahit <kmtahsinhassan.rahit@ucalgary.ca>
Created: Thursday, December 8th 2022, 1:29:19 pm
-----
Copyright (c) 2022 Tahsin Hassan Rahit, MTG-lab, University of Calgary

You should have received a copy of the license along with this program.
'''
# python -m api.gpad


from api.gene_discovery.displacy_visualizer import PatternLab
import typer
import logging
import numpy as np
import pandas as pd
from tqdm import tqdm, trange
from pathlib import Path

from rich import print

from api.gene_discovery.data_curation import Curator
from api.gene_discovery.gpad_validation import Validation
from api.gene_discovery.models import AggregationQueryFactory, AssociationInformation, GeneMap, GeneEntry

from .gene_discovery.settings import *
from .gene_discovery.omim_api_extraction import extract_gene_info, get_gene_ids, has_update, ignore_existing_genes, get_geneMaps, what_to_update


tpr = typer.Typer(pretty_exceptions_show_locals=False)


import os
from mongoengine import connect, disconnect


    

@tpr.command()
def visualize():
    entry = GeneEntry.objects(mimNumber=619239).first()
    logging.info(entry.mimNumber)
    text = ""
    if entry:
        for text_section in entry.textSectionList:
            if  text_section['textSection']['textSectionName'] == 'molecularGenetics':
                text = text_section['textSection']['textSectionContent'].replace(
                            '\n\n', ' ')
        logging.info(text[:100])
        pl = PatternLab()
        pl.show(text=text)
    else:
        logging.info("No entry found")


@tpr.command()
def compare():
    v = Validation()
    # print(v.chong_df)
    # v.get_years()
    v.combine()
    v.evaluate_match()
    v.save(as_excel=True)
    # v.plot()


@tpr.command()
def export():
    aqf = AggregationQueryFactory()
    aqf.export_associations(data_dir / f"export_AssociationInformation_May2023_v5.xlsx")

@tpr.command()
def omim(dry_run: bool = typer.Option(False, help="If TRUE, run analysis without updating database")):
    print(f"\n:robot:..GPAD Started..:robot:\n")
    
    # # Get GeneMap entries
    # all_mims = get_geneMaps()
    # print(f"Identify Associations [green]:heavy_check_mark:[/green]\n")
    # logging.info(all_mims)
    
    # Identify Entries to fetch
    mims_to_fetch = what_to_update()
    print(f"[bold red]{len(mims_to_fetch)}[/bold red] entries to be extracted from OMIM API.\n")
    
    # Extract from OMIM API
    extracted = extract_gene_info(mims_to_fetch)
    print(f"[bold blue]{len(extracted)}[/bold blue] genes successfully extracted.\n")
    
    # Apply NLP
    curation = Curator()
    # curation.curate([], detect='all', force_update=True, dry_run=dry_run)
    # curation.curate([603136], force_update=True, dry_run=True)
    curation.curate(extracted)
    
    print(f":white_heavy_check_mark: DONE!")


@tpr.command()
def stat():
    # print("Analyzing OMIM's Gene Map")
    # gm = GeneMap.objects
    # assocs = []
    # c = 0
    # for g in tqdm(gm):
    #     for p in g.phenotypes:
    #         assocs.append((g.mimNumber, p.mimNumber))
                                
    # assocs = np.array(assocs)
    
    # print(f"Total {len(list(set(assocs[:,0])))} unique genes")
    # print(f"Total {len(list(set(assocs[:,1])))} unique phenotypes")
    # print(f"[red]Total {assocs.shape[0]} gene-phenotype associations[/red]")
    # print("[hr]")
    
    print("Analyzing GPAD's Associations")
    ai = AssociationInformation.objects
    assocs = []
    for assoc in ai:
        assocs.append((assoc.gene_mimNumber, assoc.pheno_mimNumber, assoc.mapping_key))
    assocs = np.array(assocs)
    
    print(f"Total {len(list(set(assocs[:,0])))} unique genes")
    print(f"Total {len(list(set(assocs[:,1])))} unique phenotypes")
    print(f"[red]Total {assocs.shape[0]} gene-phenotype associations[/red]")

    # filtered_ai = AssociationInformation.objects(Q((mapping_key=3) & ())).only('pheno_mimNumber')
    phenos = AssociationInformation.objects(mapping_key__ne=3).only('pheno_mimNumber')
    print(f"Total {filtered_ai.count()} GDA with mapping key 3")
    print(f"Total {len(phenos)} GDA with mapping key other than 3")
    # print(f"[red]{c}[/red]")
    
    # e = GeneEntry.objects(prefix='#').only('mimNumber')
    # ids = [_e['mimNumber'] for _e in e]
    # c = list(set(ids))
    # print(f"[red]{len(c)}[/red]")


    
if __name__ == '__main__':
    tpr()

