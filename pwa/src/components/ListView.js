import React,  { useState, useEffect } from 'react';
import MaterialTable from "material-table";
import {AiOutlineLoading3Quarters} from 'react-icons/ai';
import Grid from '@material-ui/core/Grid';
import { SearchResultView } from './SearchView';

function ListView() {
    var date_from = new Date();
    date_from.setDate(date_from.getDate() - 30);
    const [error, setError] = useState(null);
    const [isLoaded, setIsLoaded] = useState(false);
    const [items, setItems] = useState([]);
    console.log(process.env)
    
    let url = "http://localhost:5555/api/v1/new/" + date_from.toISOString().slice(0,-1)
    // url += 'per_page=' + query.pageSize
    // url += '&page=' + (query.page + 1)
    // Note: the empty deps array [] means
    // this useEffect will run once
    // similar to componentDidMount()
    useEffect(() => {
      fetch(url)
        .then(res => res.json())
        .then(
          (result) => {
            setIsLoaded(true);
            setItems(result);
          },
          // Note: it's important to handle errors here
          // instead of a catch() block so that we don't swallow
          // exceptions from actual bugs in components.
          (error) => {
            setIsLoaded(true);
            setError(error);
          }
        )
    }, [])
  
    if (error) {
      return <div>Error: {error.message}</div>;
    } else if (!isLoaded) {
      return <AiOutlineLoading3Quarters />;
    } else {
      return (
        <MaterialTable
                title="Recent GPAD reported by OMIM"
                columns={[
                { title: "Gene Symbols", field: "gene_symbols", 
                  render: rowData => <a href={"https://omim.org/entry/"+rowData.gene_mimNumber} target="_blank" rel="noopener noreferrer">{rowData.gene_symbols}</a>,                  
                  cellStyle: {
                    backgroundColor: '#c4deff'
                  },
                },
                { title: "Phenotype", field: "phenotype" },
                { title: "GP association made in", field: "evidence.publication_evidence.year" },
                { title: "Potential earliest matching patient", field: "cohort.publication_evidence.year"},
                { title: "# of matching patients", field: "cohort.cohort_count"},
                { title: "Potential earliest model organism study", field: "animal_model.publication_evidence.year" }
                ]}
                data={items}
                detailPanel={[
                  {
                    tooltip: 'Show Detail',
                    render: rowData => { return(
                    <Grid container direction="row" justify="center" alignItems="center">
                      <SearchResultView query={rowData.gene_mimNumber} />
                    </Grid>) }
                    // rowData => {
                    //   return (
                    //     <div>
                    //       <a href={"https://pubmed.ncbi.nlm.nih.gov/"+rowData.earliest_phenotype_association.pmid} target="_blank" rel="noopener noreferrer" >
                    //         {rowData.earliest_phenotype_association.author} ({rowData.earliest_phenotype_association.year})
                    //       </a>
                    //     </div>
                    //   )
                    // },
                  }]}
                options={{
                  headerStyle: {
                    backgroundColor: '#01579b',
                    color: '#FFF'
                  }
                }}
            />       
      );
    }
  }

export default ListView;