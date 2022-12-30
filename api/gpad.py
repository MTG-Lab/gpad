'''
Author: Tahsin Hassan Rahit <kmtahsinhassan.rahit@ucalgary.ca>
Created: Thursday, December 8th 2022, 1:29:19 pm
-----
Copyright (c) 2022 Tahsin Hassan Rahit, MTG-lab, University of Calgary

You should have received a copy of the license along with this program.
'''
# python -m api.gpad


from api.gene_discovery.model_copy import copy
import typer
import logging
import numpy as np
from tqdm import tqdm, trange
from pathlib import Path

from rich import print

from api.gene_discovery.data_curation import Curator
from api.gene_discovery.gpad_validation import Validation
from api.gene_discovery.models import AssociationInformation, GeneMap

from .gene_discovery.settings import *
from .gene_discovery.omim_api_extraction import extract_gene_info, get_gene_ids, has_update, ignore_existing_genes, get_geneMaps, what_to_update


tpr = typer.Typer()




@tpr.command()
def cp():
    copy()



@tpr.command()
def compare():
    v = Validation()
    v.get_years()
    v.evaluate_match()
    v.save(as_excel=True)
    # v.plot()


@tpr.command()
def omim():
    print(f"\n:robot:..GPAD Started..:robot:\n")
    
    # Get GeneMap entries
    # all_mims = get_geneMaps()
    print(f"Identify Associations [green]:heavy_check_mark:[/green]\n")
    
    # # Identify Entries to fetch
    # mims_to_fetch = what_to_update()
    # print(f"[bold red]{len(mims_to_fetch)}[/bold red] entries to be extracted from OMIM API.\n")
    
    # # # # Extract from OMIM API
    # extracted = extract_gene_info(mims_to_fetch)
    # print(f"[bold blue]{len(extracted)}[/bold blue] genes successfully extracted.\n")
    
    # # Apply NLP
    curation = Curator()
    curation.curate([400020], force_update=True)
    # curate(extracted)
    
    print(f":white_heavy_check_mark: DONE!")


@tpr.command()
def stat():
    print("Analyzing OMIM's Gene Map")
    gm = GeneMap.objects
    assocs = []
    for g in gm:
        for p in g.phenotypes:
            assocs.append((g.mimNumber, p.mimNumber))
    assocs = np.array(assocs)
    
    print(f"Total {len(list(set(assocs[:,0])))} unique genes")
    print(f"Total {len(list(set(assocs[:,1])))} unique phenotypes")
    print(f"Total {assocs.shape[0]} gene-phenotype associations")

    print("Analyzing GPAD's Associations")
    ai = AssociationInformation.objects
    assocs = []
    for assoc in ai:
        assocs.append((assoc.gene_mimNumber, assoc.pheno_mimNumber))
    assocs = np.array(assocs)
    
    print(f"Total {len(list(set(assocs[:,0])))} unique genes")
    print(f"Total {len(list(set(assocs[:,1])))} unique phenotypes")
    print(f"Total {assocs.shape[0]} gene-phenotype associations")

if __name__ == '__main__':
    tpr()

