import React,  { useState, useEffect } from 'react';
import { scaleOrdinal } from 'd3-scale';
import { schemeDark2 } from 'd3-scale-chromatic';
import { BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, Label, ResponsiveContainer } from 'recharts';
import {AiOutlineLoading3Quarters } from 'react-icons/ai';


export default function ModelOrganismYearlyTrendView() {
    const [error, setError] = useState(null);
    const [isLoaded, setIsLoaded] = useState(false);
    const [items, setItems] = useState([]);
    const colors = scaleOrdinal(schemeDark2).range();
    
    // Note: the empty deps array [] means
    // this useEffect will run once
    // similar to componentDidMount()
    useEffect(() => {
      fetch("http://localhost:5555/api/v1/mo_yearly_trend")
        .then(res => res.json())
        .then(
          (result) => {
            setIsLoaded(true);
            setItems(result.data);
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
        <ResponsiveContainer height={500} >
          <BarChart width={500} height={300} data={items} 
            // layout="vertical"
            barCategoryGap={8}
            barGap={2}
            margin={{
              top: 20,
              right: 30,
              left: 20,
              bottom: 5,
            }}>
            {/* <Bar dataKey="count" >
              {items.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={colors[index % 20]} />
              ))}
            </Bar> */}
            <XAxis dataKey="year" position="insideStart" tickCount={10} minTickGap={10} />
            <YAxis>
              <Label value="Total # GPAD study with the organism" position="insideBottomLeft" angle="-90" offset={7} />
            </YAxis>
            <Tooltip />
            <Legend />
            <CartesianGrid strokeDasharray="6 6" />
            <Bar dataKey="Mouse" stackId="a" fill={colors[0]} />
            <Bar dataKey="Drosophila" stackId="a" fill={colors[1]} />
            <Bar dataKey="Zebrafish" stackId="a" fill={colors[2]} />
            <Bar dataKey="Rat/Rodents" stackId="a" fill={colors[3]} />
            <Bar dataKey="Yeast" stackId="a" fill={colors[4]} />
            <Bar dataKey="C. elegans" stackId="a" fill={colors[5]} />
            <Bar dataKey="Xenopus" stackId="a" fill={colors[6]} />
            <Bar dataKey="Pea Plant" stackId="a" fill={colors[7]} />
            <Bar dataKey="Other" stackId="a" fill={colors[8]} />
          </BarChart>
        </ResponsiveContainer>
      );
    }
  }
