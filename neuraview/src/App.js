import React from 'react';
import './App.css';
import FileUpload from './FileUpload';  // Import the FileUpload component

function App() {
  return (
    <div className="App">
      <h1>Welcome to NeuraView</h1>
      <FileUpload />  {/* Add the FileUpload component here */}
    </div>
  );
}

export default App;

