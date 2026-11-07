import { createRoot } from "react-dom/client";
import { Routes } from "@generouted/react-router";
import { I18nProvider } from "@/i18n";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <I18nProvider><Routes /></I18nProvider>,
);
