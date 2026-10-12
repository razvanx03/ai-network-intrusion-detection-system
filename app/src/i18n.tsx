import React, { createContext, useContext, useState, useEffect } from "react";
import { STORAGE_KEYS } from "@/constants";

export type Language = "ro" | "en";
export type Theme = "dark" | "light";

export const translations = {
  ro: {
    // App & Layout
    app_title: "AI NIDS Portal",
    hub_title: "AI NIDS",
    nav_dashboard: "Live Dashboard",
    nav_connections: "Zeek Flows",
    sensor_label: "Senzor",
    sensor_mock: "Simulare (Mod Mock)",
    sensor_remote: "Agent VM la Distanta",
    sensor_offline: "Deconectat",
    logout: "Deconectare",

    // Settings Dropdown
    settings_title: "Setari",
    settings_language: "Limba",
    settings_theme: "Tema",
    lang_ro: "Romana",
    lang_en: "English",
    theme_dark: "Intunecat",
    theme_light: "Luminos",

    // Login Page
    login_card_title: "Autentificare Administrator",
    login_username: "Nume utilizator",
    login_password: "Parola",
    login_button: "Conectare in Consola NIDS",
    login_verifying: "Se verifica...",
    login_error_default: "Autentificare esuata. Verificati credentialele.",

    // Dashboard Console
    console_title: "Consola & Comenzi Operative",
    btn_fetch_analyze: "Preia & Analizeaza Loguri",
    btn_analyzing: "AI Analizeaza fluxurile...",
    btn_reset_sensor: "Curata Loguri de pe VM",
    btn_resetting_sensor: "Resetare VM...",
    btn_reset_db: "Reset DB",
    btn_clearing_db: "Stergere...",
    confirm_clear_db: "Sigur doriti sa stergeti toate alertele si conexiunile din baza de date pentru un test curat?",
    analysis_done: "Analiza finalizata: {conns} conexiuni noi, {alerts} alerte detectate.",
    analysis_error: "Eroare la preluarea logurilor: {error}",
    sensor_reset_msg: "Senzor VM: {msg}",
    sensor_reset_error: "Eroare resetare senzor: {error}",
    clear_db_error: "Eroare curatare date: {error}",

    // Dashboard Stats Cards
    stats_total_alerts: "Total Alerte",
    stats_unresolved: "nerezolvate in asteptare",
    stats_critical: "Alerte Critice",
    stats_critical_sub: "SSH Brute-Force & Floods de volum",
    stats_high: "Alerte Ridicate (High)",
    stats_high_sub: "Port Scanning & Recunoastere",
    stats_connections: "Conexiuni Zeek Inspectate",
    stats_connections_sub: "Metadate de sesiune persistate",

    // Dashboard Alerts Table
    feed_title: "Feed Alerte de Securitate",
    filter_all_severities: "Toate Severitatile",
    th_severity: "Severitate",
    th_attack_type: "Tip Atac",
    th_source: "Sursa (Atacator)",
    th_destination: "Destinatie",
    th_detector: "Model / Detector",
    th_mitre: "MITRE ATT&CK",
    th_status: "Status",
    th_action: "Actiune",
    btn_resolve: "Rezolva",
    no_alerts: "Nu exista alerte active pentru filtrul curent.",
    no_alerts_hint: "Apasati pe butonul „Preia & Analizeaza Loguri” pentru a declansa ingestia de teste.",

    // Connections Page
    conn_title: "Fluxuri de Retea Zeek (conn.log)",
    filter_all_protos: "Toate Protocoalele",
    btn_refresh: "Reimprospateaza",
    btn_refreshing: "Se incarca...",
    conn_history_title: "Istoric Sesiuni Inregistrate",
    conn_total: "Total inregistrari",
    no_connections: "Nu exista conexiuni inregistrate in baza de date.",
    th_uid: "UID",
    th_protocol: "Protocol",
    th_service: "Serviciu",
    th_conn_state: "Stare Conexiune",
    th_duration: "Durata",
    th_bytes: "Bytes (Orig / Resp)",
    th_packets: "Pachete",
  },
  en: {
    // App & Layout
    app_title: "AI NIDS Portal",
    hub_title: "AI NIDS",
    nav_dashboard: "Live Dashboard",
    nav_connections: "Zeek Flows",
    sensor_label: "Sensor",
    sensor_mock: "Simulation (Mock Mode)",
    sensor_remote: "Remote VM Agent",
    sensor_offline: "Offline",
    logout: "Log out",

    // Settings Dropdown
    settings_title: "Settings",
    settings_language: "Language",
    settings_theme: "Theme",
    lang_ro: "Romanian",
    lang_en: "English",
    theme_dark: "Dark",
    theme_light: "Light",

    // Login Page
    login_card_title: "Administrator Authentication",
    login_username: "Username",
    login_password: "Password",
    login_button: "Sign In to NIDS Console",
    login_verifying: "Verifying...",
    login_error_default: "Authentication failed. Check your credentials.",

    // Dashboard Console
    console_title: "Console & Operational Commands",
    btn_fetch_analyze: "Fetch & Analyze Logs",
    btn_analyzing: "AI Analyzing flows...",
    btn_reset_sensor: "Clear VM Sensor Logs",
    btn_resetting_sensor: "Resetting VM...",
    btn_reset_db: "Reset DB",
    btn_clearing_db: "Clearing...",
    confirm_clear_db: "Are you sure you want to delete all alerts and connections from the database for a clean test?",
    analysis_done: "Analysis completed: {conns} new connections, {alerts} alerts detected.",
    analysis_error: "Error fetching logs: {error}",
    sensor_reset_msg: "VM Sensor: {msg}",
    sensor_reset_error: "Error resetting sensor: {error}",
    clear_db_error: "Error clearing database: {error}",

    // Dashboard Stats Cards
    stats_total_alerts: "Total Alerts",
    stats_unresolved: "unresolved pending",
    stats_critical: "Critical Alerts",
    stats_critical_sub: "SSH Brute-Force & Volume Floods",
    stats_high: "High Alerts",
    stats_high_sub: "Port Scanning & Reconnaissance",
    stats_connections: "Inspected Zeek Connections",
    stats_connections_sub: "Persisted session metadata",

    // Dashboard Alerts Table
    feed_title: "Security Alerts Feed",
    filter_all_severities: "All Severities",
    th_severity: "Severity",
    th_attack_type: "Attack Type",
    th_source: "Source (Attacker)",
    th_destination: "Destination",
    th_detector: "Model / Detector",
    th_mitre: "MITRE ATT&CK",
    th_status: "Status",
    th_action: "Action",
    btn_resolve: "Resolve",
    no_alerts: "No active alerts matching the current filter.",
    no_alerts_hint: "Click 'Fetch & Analyze Logs' to trigger test data ingestion.",

    // Connections Page
    conn_title: "Zeek Network Flows (conn.log)",
    filter_all_protos: "All Protocols",
    btn_refresh: "Refresh",
    btn_refreshing: "Loading...",
    conn_history_title: "Recorded Session History",
    conn_total: "Total records",
    no_connections: "No connections recorded in the database.",
    th_uid: "UID",
    th_protocol: "Protocol",
    th_service: "Service",
    th_conn_state: "Conn State",
    th_duration: "Duration",
    th_bytes: "Bytes (Orig / Resp)",
    th_packets: "Packets",
  },
} as const;

export type TranslationKey = keyof typeof translations.ro;

interface I18nContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
  theme: Theme;
  setTheme: (theme: Theme) => void;
  t: (key: TranslationKey, params?: Record<string, string | number>) => string;
}

const I18nContext = createContext<I18nContextType | null>(null);

export const I18nProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [language, setLanguageState] = useState<Language>(() => {
    const saved = localStorage.getItem(STORAGE_KEYS.LANGUAGE) as Language | null;
    return saved === "en" || saved === "ro" ? saved : "ro";
  });

  const [theme, setThemeState] = useState<Theme>(() => {
    const saved = localStorage.getItem(STORAGE_KEYS.THEME) as Theme | null;
    return saved === "light" || saved === "dark" ? saved : "dark";
  });

  const setLanguage = (lang: Language) => {
    setLanguageState(lang);
    localStorage.setItem(STORAGE_KEYS.LANGUAGE, lang);
  };

  const setTheme = (newTheme: Theme) => {
    setThemeState(newTheme);
    localStorage.setItem(STORAGE_KEYS.THEME, newTheme);
  };

  // Sync theme with HTML root document class
  useEffect(() => {
    const root = document.documentElement;
    if (theme === "dark") {
      root.classList.add("dark");
      root.classList.remove("light");
      root.setAttribute("data-theme", "dark");
    } else {
      root.classList.add("light");
      root.classList.remove("dark");
      root.setAttribute("data-theme", "light");
    }
  }, [theme]);

  const t = (key: TranslationKey, params?: Record<string, string | number>): string => {
    const langDict = translations[language] || translations.ro;
    let text: string = langDict[key] || translations.ro[key] || key;
    if (params) {
      Object.entries(params).forEach(([paramKey, val]) => {
        text = text.replace(new RegExp(`\\{${paramKey}\\}`, "g"), String(val));
      });
    }
    return text;
  };

  return (
    <I18nContext.Provider value={{ language, setLanguage, theme, setTheme, t }}>
      {children}
    </I18nContext.Provider>
  );
};

export function useI18n(): I18nContextType {
  const ctx = useContext(I18nContext);
  if (!ctx) {
    throw new Error("useI18n must be used within an I18nProvider");
  }
  return ctx;
}
