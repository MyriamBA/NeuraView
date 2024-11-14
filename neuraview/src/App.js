import React from 'react';
import './App.css';
import FileUpload from './FileUpload';  // Import the FileUpload component
import FeatureEngineeringButton from './FeatureEngineeringButton';  // Import the Feature Engineering component


function App() {
  return (
    <div className="App">
      <h1>Welcome to NeuraView</h1>
      <FileUpload />  {/* Add the FileUpload component  */}
      <FeatureEngineeringButton />  {/* Feature Engineering Button component */}

    </div>
  );
}

export default App;


