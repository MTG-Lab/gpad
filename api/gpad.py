'''
Author: Tahsin Hassan Rahit <kmtahsinhassan.rahit@ucalgary.ca>
Created: Thursday, December 8th 2022, 1:29:19 pm
-----
Copyright (c) 2022 Tahsin Hassan Rahit, MTG-lab, University of Calgary

You should have received a copy of the license along with this program.
'''
# python -m api.gpad


import typer
import logging
from tqdm import tqdm, trange
from pathlib import Path

from rich import print

from api.gene_discovery.data_curation import Curator
from api.gene_discovery.gpad_validation import Validation

from .gene_discovery.settings import *
from .gene_discovery.omim_api_extraction import extract_gene_info, get_gene_ids, has_update, ignore_existing_genes, get_geneMaps, what_to_update


tpr = typer.Typer()


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
    all_mims = get_geneMaps()
    print(f"Identify Associations [green]:heavy_check_mark:[/green]\n")
    
    # Identify Entries to fetch
    mims_to_fetch = what_to_update()
    print(f"[bold red]{len(mims_to_fetch)}[/bold red] genes to be extracted from OMIM API.\n")
    
    # Extract from OMIM API
    extracted = extract_gene_info(mims_to_fetch)
    print(f"[bold blue]{len(extracted)}[/bold blue] genes successfully extracted.\n")
    
    # Apply NLP
    curation = Curator()
    curation.curate(extracted)
    # curate(extracted)
    
    print(f":white_heavy_check_mark: DONE!")


if __name__ == '__main__':
    tpr()

