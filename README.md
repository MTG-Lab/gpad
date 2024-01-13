# Gene-Phenotype Association Discovery (GPAD) 🧬🔍
An interactive web-based tool for analyzing, interrogating, and visualizing the gene-disease association on **Online Mendelian Inheritance in Man** [(OMIM)](https://www.ncbi.nlm.nih.gov/omim).

Explore GPAD on any modern internet browser! Whether you're on a PC, tablet, or mobile phone, our platform is optimized for your convenience.

## 🛠 Installation

### Prerequisites
- **OMIM API key**: Request yours from the OMIM team [here](https://www.omim.org/api).
- **Docker**: GPAD runs in Docker containers, ensuring a consistent and isolated environment across different machines. [Download Docker](https://www.docker.com/get-started) if you haven't already. It's a powerful tool that packages applications and their dependencies into a single container that can run anywhere, streamlining deployment and testing.


### Steps to Get Started:
1. **Clone the Repository**
   - Use the command: `git clone git@github.com:MTG-Lab/gpad.git`
2. **Environment Setup**
   - Create a `.env` file using our `example.env` as a template.
   - Replace values in the `.env` file with your own. You do not have to change the `MONGO_URI` if you are using docker.
3. **Build and Run with Docker**
   - Execute: `docker compose up -d`

🚀 Post-setup, access the application at `http://localhost:3001`. Initially, you'll be greeted with a blank page as there's no data yet.

### Populating Data
GPAD leverages the OMIM API for textual data, which is then processed to extract relevant information. This is a breeze with just one command: 
```bash
docker exec -it gpad_api python -m api.gpad omim
```
⏳ The data population depends on your internet speed. Be patient!

### 📌 Important Note
OMIM API limits 250 requests per day. Because of that all associations/entries from OMIM will not be processed in a single day. Therefore, you might need to run the above command multiple times. However, it will not process the data that is already processed. It will start from where it left off.

🔎 Once complete, you'll see the data come to life in the application!

## 🌟 Enjoy exploring GPAD!
