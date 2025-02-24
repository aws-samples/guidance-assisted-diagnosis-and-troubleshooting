import { useEffect, useState } from "react";
import Dashboard from './components/Dashboard';
import {useAwsCredentials} from "./AWSCredentialsContext"
import "./App.css"

import { $user } from './stores/users';



const App = () => {
  const [loading, setLoading] = useState(true);
  const awsCredentials = useAwsCredentials();


  useEffect(() => {
    if (awsCredentials) {
      $user.set({
        email: awsCredentials.username,
        username: awsCredentials.username,
        awsCredentials: awsCredentials,
      })
      setLoading(false);
    }
  }, [awsCredentials]);

  if (loading) {
    return <div>Loading...</div>; 
  }


  return (
    <Dashboard  />
  )
};

export default App;
