import React,  { useState, useEffect } from 'react';
import {AiOutlineLoading3Quarters} from 'react-icons/ai';
import { LineChart, Line, Label, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

function TrendView() {
    const [error, setError] = useState(null);
    const [isLoaded, setIsLoaded] = useState(false);
    const [items, setItems] = useState([]);
    // Note: the empty deps array [] means
    // this useEffect will run once
    // similar to componentDidMount()
    useEffect(() => {
      fetch("http://206.12.96.161:5555/api/v1/trend")
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
        <LineChart data={items}>
          <Line type="monotone" dataKey="earliest_phenotype_association" name="GP Association" stroke="#ef1919" isAnimationActive='false' />
          {/* <Line type="monotone" dataKey="earliest_av_association" name="Variant Association" stroke="#ffa4ff" /> */}
          <Line type="monotone" dataKey="earliest_cohort" name="GP using independent cohort" stroke="#4bbf30" activeDot={{ r: 8 }} />
          <Line type="monotone" dataKey="earliest_phenotype_specific_animal_model" name="GP using model organism" stroke="#396fe8" />
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="_id" domain={[1985, 'auto']}>
            <Label value="Publication Year" offset={-5} position="insideBottom" />
          </XAxis>
          <YAxis>
            <Label value="Total # of novel GPAD" position="insideLeft" angle="-90" offset={0} />
          </YAxis>
          <Tooltip />
          <Legend verticalAlign="top" height={36} />
        </LineChart>
        </ResponsiveContainer>
      );
    }
  }

export default TrendView;