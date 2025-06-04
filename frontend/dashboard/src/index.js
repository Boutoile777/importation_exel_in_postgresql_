import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css'; // si tu utilises Tailwind, sinon retire cette ligne

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
