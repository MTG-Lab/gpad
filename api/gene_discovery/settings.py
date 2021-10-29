'''
Author: Tahsin Hassan Rahit <kmtahsinhassan.rahit@ucalgary.ca>
Created: Friday, March 5th 2021, 12:42:16 pm
-----
Copyright (c) 2021 Tahsin Hassan Rahit, MTG-lab, University of Calgary

You should have received a copy of the license along with this program.
'''

import os
import dotenv
import logging
from pathlib import Path
from mongoengine import connect
from pymongo import MongoClient

project_dir = Path(__file__).parents[2]
data_dir = project_dir / 'data'

dotenv_path = project_dir / '.env'
dotenv.load_dotenv(dotenv_path)

OMIM_API_KEY = os.getenv("OMIM_API_KEY")
OMIM_RESPONSE_LIMIT = 20    # OMIM limit 20 entries per request
NCBI_API_KEY = os.getenv("NCBI_API_KEY")

log_fmt = "[%(asctime)s - %(levelname)s - %(filename)s:%(lineno)s - %(funcName)s() ] %(message)s"
logging.basicConfig(filename=project_dir/'logs'/'app.log', filemode='w', level=logging.DEBUG, format=log_fmt)

# Connect to mongodb
# connect(
#     db = os.getenv("MONGO_DB", "gene_discovery"),
#     host = os.getenv("MONGO_HOST", "localhost"),
#     port = os.getenv("MONGO_PORT", 27017),
#     username = os.getenv("MONGO_USER", None),
#     password = os.getenv("MONGO_PASS", None)
# )

MONGO_URI = os.getenv("MONGO_URI")
db = MongoClient(MONGO_URI)['gene_discovery']
connect(host=MONGO_URI)