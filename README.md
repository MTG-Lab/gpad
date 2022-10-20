# GPAD
An interactive web-basd tool for analyzing, interrogating, and visualizing the **Online Mendelian Inheritance in Man** [(OMIM)](https://www.ncbi.nlm.nih.gov/omim).

This tool runs on all modern internet browser applications and we encourge you to explore this tool on a PC, tablet, or mobile phone.


## Installation
**Prerequisite**: Obtain OMIM API key by requesting OMIM team here: [https://www.omim.org/api](https://www.omim.org/api)
1. Clone this repo to your local machine using `https://github.com/MTG-Lab/Shiny-OMIM`
2. Create your own `.env` and . `.flaskenv` file using provided `example.env` for specifying environment variables. Replace values with your own.
3. Build and run docker containers `docker compose up`
4. Extract OMIM data `docker exec -it gpad_api make data-init`

## Running
Data backend prepares data in a 2 step process.
1. Collect data using OMIM API and save it as it is in MongoDB collection using `gene_discovery/omim_api_extraction.py`
   - To run these script - `python -m gene_discovery.omim_api_extraction --init` 
     - Note that OMIM API limits 250 requests per day. Therefore you might need to work on the data for multiple days. Do not run the above command with `--init` flag. Because it will process data from the beggining. Instead run following: `python -m gene_discovery.omim_api_extraction` 
2. Curate/process collected data according the the need using `gene_discovery/data_curation.py`
   - To run these script - `python -m gene_discovery.data_curation`

## Features
## Usage (Optional)
## Documentation (Optional)
## Tests (Optional)

