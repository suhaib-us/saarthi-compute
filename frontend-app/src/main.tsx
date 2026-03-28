import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App";

const CONVEX_URL = import.meta.env.VITE_CONVEX_URL as string | undefined;
const convexConfigured = !!CONVEX_URL && !CONVEX_URL.includes("your_");

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
    {convexConfigured && (
      <div className="fixed bottom-4 right-4 text-xs bg-green-50 text-green-700 px-2 py-1 rounded-full border border-green-200 shadow-sm">
        Convex connected
      </div>
    )}
  </StrictMode>,
);
