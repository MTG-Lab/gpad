import React,  { useState, useEffect } from 'react';
import { scaleOrdinal } from 'd3-scale';
import { schemeCategory10 } from 'd3-scale-chromatic';
import { BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, Label, ResponsiveContainer } from 'recharts';
import {AiOutlineLoading3Quarters } from 'react-icons/ai';


export default function PopulationTrendView() {
    const [error, setError] = useState(null);
    const [isLoaded, setIsLoaded] = useState(false);
    const [items, setItems] = useState([]);
    const colors = scaleOrdinal(schemeCategory10).range();
    
    // Note: the empty deps array [] means
    // this useEffect will run once
    // similar to componentDidMount()
    useEffect(() => {
      fetch("http://localhost:5555/api/v1/population_trend")
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
          <BarChart width={150} height={40} data={items}>
            <Bar dataKey="count" fill="#8884d8" >
              {items.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={colors[index % 20]} />
              ))}
            </Bar>
            <XAxis dataKey="_id" position="insideStart" allowDataOverflow="true" />
            <YAxis>
              <Label value="Total # GPAD study with the population" position="insideBottomLeft" angle="-90" offset={7} />
            </YAxis>
            <Tooltip />
            <Legend />
            <CartesianGrid strokeDasharray="3 3" />
          </BarChart>
        </ResponsiveContainer>
      );
    }
  }

// export default PopulationTrendView;