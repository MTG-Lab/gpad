import React, { useState, useEffect } from 'react';
import SearchBar from "material-ui-search-bar";
import { makeStyles } from '@material-ui/core/styles';
import Grid from '@material-ui/core/Grid';
import Card from '@material-ui/core/Card';
import Badge from '@material-ui/core/Badge';
import Chip from '@material-ui/core/Chip';
import CardActions from '@material-ui/core/CardActions';
import CardContent from '@material-ui/core/CardContent';
import Button from '@material-ui/core/Button';
import Typography from '@material-ui/core/Typography';
import { AiOutlineLoading3Quarters, AiFillBug } from 'react-icons/ai';
import { BsFillPeopleFill } from 'react-icons/bs';
import { FaNotesMedical } from 'react-icons/fa';


const useStyles = makeStyles({
  root: {
    minWidth: 275,
  },
  bullet: {
    display: 'inline-block',
    margin: '0 2px',
    transform: 'scale(0.8)',
  },
  title: {
    fontSize: 14,
  },
  pos: {
    marginBottom: 12,
  },
});


export function SearchResultView(props) {
  const classes = useStyles();
  const bull = <span className={classes.bullet}>•</span>;

  const [error, setError] = useState(null);
  const [isLoaded, setIsLoaded] = useState(false);
  const [items, setItems] = useState([]);
  const [earliest_phenotype_association, setEarliestPhenotypeAssociation] = useState({ pmid: null, author: null, year: null });
  const [earliest_cohort, setEarliestCohort] = useState({ publication_evidence: { pmid: null, author: null, year: null } });
  const [earliest_phenotype_specific_animal_model, setEarliestPhenotypeSpecificAninamModel] = useState({ publication_evidence: { pmid: null, author: null, year: null } });

  let url = "http://206.12.96.161:5555/api/v1/search?q=" + props.query
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
  }, [props])
  if (error) {
    return <div>Error: {error.message}</div>;
  } else if (!isLoaded) {
    return <AiOutlineLoading3Quarters />;
  } else {

    const cards = items.map(item =>
      <Card className={classes.root} variant="outlined">
        <CardContent>
          <Typography className={classes.title} color="textSecondary" gutterBottom>
          <a href={"https://omim.org/entry/" + item.assoc_info.gene_mim_id} target="_blank" rel="noopener noreferrer" >
            {item.assoc_info.gene_mim_id}</a>
             - {item.gene_info.geneSymbols}
          </Typography>
          <Typography className={classes.pos} color="textSecondary">
            {item.gene_info.geneName}
          </Typography>
          <Typography variant="h5" component="h2">
            {item.assoc_info.phenotype}
          </Typography>
          <br />
          <Typography variant="body2" component="p">
            {item.assoc_info.earliest_phenotype_association.year &&
              <span>
                <FaNotesMedical />
                GP association made in: <a href={"https://pubmed.ncbi.nlm.nih.gov/" + item.assoc_info.earliest_phenotype_association.pmid} target="_blank" rel="noopener noreferrer" >
                  {item.assoc_info.earliest_phenotype_association.year}
                </a>
              </span>
            }
            <br />
            {item.assoc_info.earliest_cohort.publication_evidence.year &&
              <span>
                <BsFillPeopleFill />
                Potential earliest unrelated matching patient study: <a href={"https://pubmed.ncbi.nlm.nih.gov/" + item.assoc_info.earliest_cohort.publication_evidence.pmid} target="_blank" rel="noopener noreferrer" >
                  {item.assoc_info.earliest_cohort.publication_evidence.year}
                </a> &nbsp; &nbsp;
                <Chip label={'with ' + item.assoc_info.earliest_cohort.cohort_count + ' unrelated patients'} />
              </span>
            }
            <br />
            {item.assoc_info.earliest_phenotype_specific_animal_model.publication_evidence.year &&
              <span>
                <AiFillBug />
                Potential earliest model organism study: <a href={"https://pubmed.ncbi.nlm.nih.gov/" + item.assoc_info.earliest_phenotype_specific_animal_model.publication_evidence.pmid} target="_blank" rel="noopener noreferrer" >
                  {item.assoc_info.earliest_phenotype_specific_animal_model.publication_evidence.year}
                </a> &nbsp;
                <Chip label={'with ' + item.assoc_info.earliest_phenotype_specific_animal_model.animal_name} />
              </span>
            }
            <br />
            {item.population && <span>Studied Populations: {item.population}</span>}
          </Typography>
        </CardContent>
        {/* <CardActions>
            <Button size="small">Learn More</Button>
          </CardActions> */}
      </Card>
    )

    return (
      <Grid xs={10}>
        {cards}
      </Grid>
    )
  }
}


export default function SearchView(props) {
  if (props.query) {
    return (<SearchResultView query={props.query} />)
  }
  else {
    return (<span></span>)
  }
}