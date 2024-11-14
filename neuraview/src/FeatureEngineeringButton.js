import React, { useState } from 'react';
import axios from 'axios';

const FeatureEngineeringButton = () => {
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  // Function to handle feature engineering request
  const runFeatureEngineering = async () => {
    setLoading(true); // Show loading indicator
    setMessage("");   // Clear previous messages

    try {
      // Send a POST request to the FastAPI feature engineering endpoint
      const response = await axios.post("http://localhost:5000/feature-engineering");

      // Check if the request was successful
      if (response.status === 200) {
        setMessage("Feature engineering completed successfully.");
      } else {
        setMessage("Failed to run feature engineering.");
      }
    } catch (error) {
      console.error("Error running feature engineering:", error);
      setMessage("Error: Unable to run feature engineering. Please try again.");
    } finally {
      setLoading(false); // Hide loading indicator
    }
  };

  return (
    <div>
      <button onClick={runFeatureEngineering} disabled={loading}>
        {loading ? "Running Feature Engineering..." : "Run Feature Engineering"}
      </button>
      {message && <p>{message}</p>}
    </div>
  );
};

export default FeatureEngineeringButton;
