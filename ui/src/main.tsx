import React from "react";
import ReactDOM from "react-dom/client";
import { HashRouter } from "react-router-dom";
import App from "./App";
import { UiSettingsProvider } from "./lib/ui-settings";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <UiSettingsProvider>
      <HashRouter>
        <App />
      </HashRouter>
    </UiSettingsProvider>
  </React.StrictMode>
);
