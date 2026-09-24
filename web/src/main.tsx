import React from "react";
import { createRoot } from "react-dom/client";
// First: sets the theme's colours before anything paints, so there is never a flash of the wrong one.
import "./design/theme";
import App from "./App";
import "./index.css";

const container = document.getElementById("root");
if (!container) throw new Error("#root is missing from index.html");

createRoot(container).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
