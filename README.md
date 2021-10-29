# GPAD
An interactive web-basd tool for analyzing, interrogating, and visualizing the **Online Mendelian Inheritance in Man** [(OMIM)](https://www.ncbi.nlm.nih.gov/omim).

This tool runs on all modern internet browser applications and we encourge you to explore this tool on a PC, tablet, or mobile phone.


## Installation
### Clone
- Clone this repo to your local machine using `https://github.com/MTG-Lab/Shiny-OMIM`
### Data Backend Setup
1. Ensure you have Python v3.8 or later
2. Install required python packages: `pip install -r requirements.txt`
3. Download trained nlp pipeline for spacy: `python -m spacy download en_core_web_sm`
4. If there is no `logs` and `data` folder in your project root, create these folders.
5. Create your own `.env` file using provided `example.env` for specifying environment variables. Replace values with your own.
6. Ensure you have [MongoDB](https://www.mongodb.com/) on your system either by [installing it on your system](https://www.mongodb.com/try/download/community) or using [MongoDB Docker image](https://hub.docker.com/_/mongo).
7. Specify your database credentials in your `.env` file.

### Running
Data backend prepares data in a 2 step process.
1. Collect data using OMIM API and save it as it is in MongoDB collection using `gene_discovery/omim_api_extraction.py`
   - To run these script - `python -m gene_discovery.omim_api_extraction --init`
2. Curate/process collected data according the the need using `gene_discovery/data_curation.py`
   - To run these script - `python -m gene_discovery.data_curation`

## Features
## Usage (Optional)
## Documentation (Optional)
## Tests (Optional)

