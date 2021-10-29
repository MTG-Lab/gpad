import React, {useState, useEffect } from 'react';
import { makeStyles } from '@material-ui/core/styles';
import Grid from '@material-ui/core/Grid';
import SearchBar from "material-ui-search-bar";
import ListView from './components/ListView.js';
import TrendView from './components/TrendView.js';
import ModelOrganismTrendView from './components/ModelOrganismTrendView.js';
import ModelOrganismYearlyTrendView from './components/ModelOrganismYearlyTrendView.js';
import PopulationTrendView from './components/PopulationTrendVie.js';
import SearchView from './components/SearchView.js';

import './App.css';
import CohortCountView from './components/CohortCountView.js';


const useStyles = makeStyles((theme) => ({
  root: {
    flexGrow: 1,
  }
}));

function App() {
  const classes = useStyles()
  const [value, setValue] = useState('');
  

  return (
    <div className="App">
      <link
        rel="stylesheet"
        href="https://fonts.googleapis.com/icon?family=Material+Icons"
      />
      <div className={classes.root}>
        <h1>Genotype-Phenotype Association Discovery (GPAD)</h1>
        <Grid container spacing={3} direction="row" justify="center" alignItems="center">
          <Grid item xs={10}>
            <SearchBar
              cancelOnEscape={true}
              placeholder='Search your favorite gene. Ex: CLDN11'
              // value={value}
              // onChange={() => console.log('onChange')}
              onRequestSearch={(value) => setValue(value)}
              style={{
                margin: '0 auto',
                maxWidth: 800
              }}
            />
          </Grid>
          <SearchView query={value} />
          <Grid item xs={10}>
            <ListView />
          </Grid>
          <Grid item xs={10}>
            <h2>Year wise GPAD Trend</h2>
            <TrendView />
          </Grid>
          {/* <Grid item xs={10}>
            <h2>Use of model organisms in assocation making</h2>
            <ModelOrganismTrendView />
          </Grid> */}
          <Grid item xs={10}>
            <h2>Use of model organisms in assocation making</h2>
            <ModelOrganismYearlyTrendView />
          </Grid>
          <Grid item xs={10}>
            <h2>Number of unrelated patients studied in assocation making</h2>
            <CohortCountView />
          </Grid>
          <Grid item xs={10}>
            <h2>Studied populations in assocation making</h2>
            <PopulationTrendView />
          </Grid>
        </Grid>
      </div>
      <br></br>
      <hr></hr>
      <div><h2>Tarailo-Graovac Laboratory</h2></div>
      <div><img src="csm.png" width="300px" /></div>
    </div>
  );
}

export default App;



