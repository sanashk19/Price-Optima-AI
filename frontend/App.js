import React, { useState } from "react";
import axios from "axios";
import "./App.css";
import {
  BarChart, Bar, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer
} from "recharts";

const initialForm = {
  Number_of_Riders: 50,
  Number_of_Drivers: 25,
  Location_Category: "Urban",
  Customer_Loyalty_Status: "Silver",
  Number_of_Past_Rides: 10,
  Average_Ratings: 4.5,
  Time_of_Booking: "Morning",
  Vehicle_Type: "Economy",
  Expected_Ride_Duration: 30,
  Historical_Cost_of_Ride: 200,
};

function App() {
  const [form, setForm] = useState(initialForm);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  const handleChange = (e) => {
    const { name, value, type } = e.target;
    let val = value;
    if (type === "number") {
      val = value === "" ? "" : Number(value);
    }
    setForm((prev) => ({ ...prev, [name]: val }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const { data } = await axios.post("http://127.0.0.1:8000/recommend_price", form,
        { headers: { "Content-Type": "application/json" } }
      );
      setResult(data);
    } catch (err) {
      const msg =
        err.response?.data?.detail ||
        err.message ||
        "Failed to get recommendation.";
      setError(String(msg));
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setForm(initialForm);
    setError("");
    setResult(null);
  };

  return (
    <div className="container">
      <h1>PriceOptima – Price Recommendation</h1>

      <form className="card" onSubmit={handleSubmit}>
        <div className="grid">
          <div className="field">
            <label>Number of Riders</label>
            <input
              type="number"
              min="0"
              name="Number_of_Riders"
              value={form.Number_of_Riders}
              onChange={handleChange}
              required
            />
          </div>

          <div className="field">
            <label>Number of Drivers</label>
            <input
              type="number"
              min="0"
              name="Number_of_Drivers"
              value={form.Number_of_Drivers}
              onChange={handleChange}
              required
            />
          </div>

          <div className="field">
            <label>Location Category</label>
            <select
              name="Location_Category"
              value={form.Location_Category}
              onChange={handleChange}
              required
            >
              <option>Urban</option>
              <option>Suburban</option>
              <option>Rural</option>
            </select>
          </div>

          <div className="field">
            <label>Customer Loyalty Status</label>
            <select
              name="Customer_Loyalty_Status"
              value={form.Customer_Loyalty_Status}
              onChange={handleChange}
              required
            >
              <option>Gold</option>
              <option>Silver</option>
              <option>Regular</option>
            </select>
          </div>

          <div className="field">
            <label>Number of Past Rides</label>
            <input
              type="number"
              min="0"
              name="Number_of_Past_Rides"
              value={form.Number_of_Past_Rides}
              onChange={handleChange}
              required
            />
          </div>

          <div className="field">
            <label>Average Ratings</label>
            <input
              type="number"
              min="0"
              max="5"
              step="0.01"
              name="Average_Ratings"
              value={form.Average_Ratings}
              onChange={handleChange}
              required
            />
          </div>

          <div className="field">
            <label>Time of Booking</label>
            <select
              name="Time_of_Booking"
              value={form.Time_of_Booking}
              onChange={handleChange}
              required
            >
              <option>Morning</option>
              <option>Afternoon</option>
              <option>Evening</option>
              <option>Night</option>
            </select>
          </div>

          <div className="field">
            <label>Vehicle Type</label>
            <select
              name="Vehicle_Type"
              value={form.Vehicle_Type}
              onChange={handleChange}
              required
            >
              <option>Economy</option>
              <option>Premium</option>
            </select>
          </div>

          <div className="field">
            <label>Expected Ride Duration (min)</label>
            <input
              type="number"
              min="1"
              name="Expected_Ride_Duration"
              value={form.Expected_Ride_Duration}
              onChange={handleChange}
              required
            />
          </div>

          <div className="field">
            <label>Historical Cost of Ride</label>
            <input
              type="number"
              min="1"
              step="0.01"
              name="Historical_Cost_of_Ride"
              value={form.Historical_Cost_of_Ride}
              onChange={handleChange}
              required
            />
          </div>
        </div>

        <div className="actions">
          <button type="submit" disabled={loading}>
            {loading ? "Calculating..." : "Recommend Price"}
          </button>
          <button type="button" className="secondary" onClick={resetForm} disabled={loading}>
            Reset
          </button>
        </div>

        {error && <div className="error">{error}</div>}
      </form>

      {result && (
        <div className="card result">
          <h2>Recommendation</h2>
          <div className="row">
            <span className="label">Recommended Price:</span>
            <span className="value">₹ {result.recommended_price}</span>
          </div>
          <div className="row">
            <span className="label">Predicted Completion Probability:</span>
            <span className="value">{result.predicted_completion_probability}</span>
          </div>
          {/* Analytics Section */}
    <div style={{ marginTop: "30px" }}>
      <h2>Policy Analytics Dashboard</h2>

      {/* 1️⃣ Historical vs Recommended Price Comparison */}
      <div style={{ marginTop: "20px" }}>
        <h3>Price Comparison</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={[
            { name: "Historical", price: form.Historical_Cost_of_Ride },
            { name: "Recommended", price: result.recommended_price }
          ]}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="price" fill="#7b2ff7" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* 2️⃣ Completion vs Revenue Mock Projection */}
      <div style={{ marginTop: "40px" }}>
        <h3>Completion vs Expected Revenue</h3>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart
            data={[
              { step: "T-3m", completion: 0.65, revenue: 200 },
              { step: "T-2m", completion: 0.72, revenue: 250 },
              { step: "T-1m", completion: 0.80, revenue: 310 },
              { step: "Current", completion: result.predicted_completion_probability, revenue: result.recommended_price }
            ]}
          >
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="step" />
            <YAxis yAxisId="left" orientation="left" stroke="#7b2ff7" />
            <YAxis yAxisId="right" orientation="right" stroke="#22c55e" />
            <Tooltip />
            <Legend />
            <Line yAxisId="left" type="monotone" dataKey="revenue" stroke="#7b2ff7" name="Expected Revenue (₹)" />
            <Line yAxisId="right" type="monotone" dataKey="completion" stroke="#22c55e" name="Completion %" />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  </div>
)}
      <footer>
        <p>Backend proxied at /api</p>
      </footer>
    </div>
  );
}

export default App;
