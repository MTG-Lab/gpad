'''
Author: Tahsin Hassan Rahit <kmtahsinhassan.rahit@ucalgary.ca>
Created: Monday, March 22nd 2021, 11:58:34 am
-----
Copyright (c) 2021 Tahsin Hassan Rahit, MTG-lab, University of Calgary

You should have received a copy of the license along with this program.
'''

import logging
import re
import pendulum

from rich import print
from tqdm import tqdm, trange
from mongoengine.queryset.visitor import Q

from .models import *
from .settings import *



def copy():
    ids = GeneEntry.objects.only('mimNumber')
    to_detele_ids = []
    keep = []
    for id in tqdm(ids):
        latest_entry = GeneEntry.objects(mimNumber=id['mimNumber']).order_by('-mtgUpdated').first()
        keep.append(latest_entry['_id'])
        to_delete = GeneEntry.objects(Q(mimNumber=id['mimNumber']) & Q(_id__ne=latest_entry['_id']))
        for e in to_delete:
            if e._id:
                logging.info(e._id)
                to_detele_ids.append(e['_id'])
                e.delete()
                
    print(f"Total deteled: {len(to_detele_ids)}")
