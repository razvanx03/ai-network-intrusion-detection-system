/* oxlint-disable react/only-export-components -- Project policy keeps translations and their reactive provider in this single module. */
import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
} from "react";
import { STORAGE_KEYS } from "@/constants";

export type Language = "ro" | "en";
export type Theme = "dark" | "light";

export const translations = {
  ro: {
    loading: "Se incarca...",
    retry: "Reincearca",
    stale_data: "Sunt afisate datele de la ultima actualizare reusita.",
    network_error:
      "Serverul nu este disponibil. Verificati conexiunea si reincercati.",
    operation_error: "Operatia nu a reusit. Reincercati.",
    session_expired:
      "Sesiunea a expirat sau accesul a fost revocat. Autentificati-va din nou.",
    logout_error:
      "Deconectarea nu a reusit. Sesiunea poate fi inca activa. Reincercati.",
    sensor_reset_done:
      "Cursorul senzorului a fost resetat. Logurile existente pot fi recitite.",
    clear_db_done: "Au fost sterse {conns} conexiuni si {alerts} alerte.",
    alert_resolved: "Alerta a fost rezolvata.",
    cancel: "Anuleaza",
    clear_title: "Sterge datele locale?",
    close: "Inchide",
    previous: "Inapoi",
    next: "Inainte",
    pagination: "{start}-{end} din {total}",
    navigation: "Navigatie principala",
    detector_not_configured: "Detector neconfigurat",
    detector_configured: "Detector activ",
    legacy_demo: "Istoric demonstrativ",
    legacy_demo_notice: "Totalurile includ {count} alerte istorice demonstrative; acestea nu sunt constatari validate.",
    analysis_prepared: "Pregatire finalizata: {conns} conexiuni noi, {prepared} inregistrari pregatite. Detectia nu este configurata.",
    analysis_sessions: "Sesiuni de analiza",
    analysis_no_sessions: "Nu exista sesiuni. Porniti analiza din consola.",
    analysis_select: "Selecteaza sesiunea {id}",
    analysis_status_running: "In curs",
    analysis_status_completed: "Finalizata",
    analysis_status_failed: "Esuata",
    analysis_status_interrupted: "Intrerupta",
    analysis_source_sensor: "Senzor",
    analysis_source_stored: "Date salvate",
    analysis_counts: "{imported} conexiuni noi / {prepared} inregistrari pregatite / {alerts} alerte",
    analysis_no_detector: "Datele sunt doar pregatite. Nu este configurat un detector; aceasta sesiune nu evalueaza siguranta traficului.",
    analysis_records: "Conexiunile sesiunii",
    analysis_origin: "Sursa",
    analysis_no_records: "Nu au fost pregatite conexiuni in aceasta sesiune.",
    analysis_alerts: "Alertele sesiunii",
    analysis_error_records: "Date invalide sau conexiuni selectate inexistente. Lotul care a esuat nu a fost salvat; loturile anterioare raman salvate.",
    analysis_error_sensor: "Senzorul nu a putut fi citit. Loturile deja importate raman salvate; reincercati operatia.",
    analysis_error_conflict: "Progresul citirii s-a schimbat. Reincercati operatia.",
    analysis_error_detector: "Procesarea datelor a esuat. Lotul care a esuat nu a fost salvat; loturile anterioare raman salvate.",
    analysis_error_processing: "Sesiunea a esuat. Datele deja confirmate raman salvate; reincercati operatia.",
    analysis_error_restart: "Sesiunea a fost intrerupta de repornirea serverului. Reluati manual operatia.",
    analysis_error_interrupted: "Cererea a fost intrerupta. Reluati manual operatia.",
    severity_CRITICAL: "Critica",
    severity_HIGH: "Ridicata",
    severity_MEDIUM: "Medie",
    severity_LOW: "Scazuta",
    status_NEW: "Noua",
    status_ACKNOWLEDGED: "Confirmata",
    status_RESOLVED: "Rezolvata",
    status_FALSE_POSITIVE: "Fals pozitiv",
    proto_tcp: "TCP",
    proto_udp: "UDP",
    proto_icmp: "ICMP",
    state_SF: "SF (Normal)",
    state_S0: "S0 (Fara SYN-ACK)",
    state_REJ: "REJ (Respins)",
    attack_ssh: "Tentative repetate SSH",
    attack_scan: "Scanare de porturi",
    attack_dos: "DoS / SYN Flood",
    attack_anomaly: "Anomalie statistica",
    chart_total: "Total",
    username_placeholder: "Nume utilizator",

    // App & Layout
    app_title: "AI NIDS Portal",
    hub_title: "AI NIDS",
    nav_dashboard: "Live Dashboard",
    nav_connections: "Zeek Flows",
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
    btn_analyzing: "Se analizeaza fluxurile...",
    btn_reset_sensor: "Reseteaza cursorul senzorului",
    btn_resetting_sensor: "Resetare cursor...",
    btn_reset_db: "Reset DB",
    btn_clearing_db: "Stergere...",
    confirm_clear_db:
      "Sigur doriti sa stergeti alertele, conexiunile si istoricul sesiunilor de analiza?",
    analysis_done:
      "Analiza finalizata: {conns} conexiuni noi, {alerts} alerte detectate.",

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
    no_alerts: "Nu exista alerte pentru filtrul curent.",

    // Connections Page
    conn_title: "Fluxuri de Retea Zeek (conn.log)",
    filter_all_protos: "Toate Protocoalele",
    btn_refresh: "Reimprospateaza",
    conn_history_title: "Istoric Sesiuni Inregistrate",
    no_connections: "Nu exista conexiuni inregistrate in baza de date.",
    th_uid: "UID",
    th_protocol: "Protocol",
    th_service: "Serviciu",
    th_conn_state: "Stare Conexiune",
    th_duration: "Durata (s)",
    th_bytes: "Bytes (Orig / Resp)",
    th_packets: "Pachete",

    // 404 Not Found Page
    not_found_title: "Pagina nu a fost gasita",
    not_found_desc:
      "Ruta pe care ati incercat sa o accesati nu exista in aplicatie.",
    not_found_back_dashboard: "Inapoi la Dashboard",
    not_found_back_login: "Inapoi la Autentificare",

    // Charts & Analytics
    chart_attacks_title: "Vectori de Atac Detectati",
    chart_severity_title: "Matrice Severitate Amenintari",
    chart_ip_title: "Top Surse Atacatoare (IP)",
    chart_no_data: "Nu exista date de afisat in grafic",

    // Report Export
    btn_export_csv: "Export CSV",
    btn_export_json: "Export JSON",
    btn_exporting: "Se descarca...",
  },
  en: {
    loading: "Loading...",
    retry: "Retry",
    stale_data: "Showing data from the last successful update.",
    network_error: "Server unavailable. Check your connection and retry.",
    operation_error: "The operation failed. Please retry.",
    session_expired:
      "Your session expired or access was revoked. Sign in again.",
    logout_error:
      "Sign out failed. Your session may still be active. Please retry.",
    sensor_reset_done: "Sensor cursor reset. Existing logs can be read again.",
    clear_db_done: "Deleted {conns} connections and {alerts} alerts.",
    alert_resolved: "Alert resolved.",
    cancel: "Cancel",
    clear_title: "Delete local data?",
    close: "Close",
    previous: "Previous",
    next: "Next",
    pagination: "{start}-{end} of {total}",
    navigation: "Main navigation",
    detector_not_configured: "Detector not configured",
    detector_configured: "Detector active",
    legacy_demo: "Demo history",
    legacy_demo_notice: "Totals include {count} historical demo alerts; these are not validated findings.",
    analysis_prepared: "Preparation completed: {conns} new connections, {prepared} records prepared. Detection is not configured.",
    analysis_sessions: "Analysis sessions",
    analysis_no_sessions: "No sessions yet. Start an analysis from the console.",
    analysis_select: "Select session {id}",
    analysis_status_running: "Running",
    analysis_status_completed: "Completed",
    analysis_status_failed: "Failed",
    analysis_status_interrupted: "Interrupted",
    analysis_source_sensor: "Sensor",
    analysis_source_stored: "Stored records",
    analysis_counts: "{imported} new connections / {prepared} records prepared / {alerts} alerts",
    analysis_no_detector: "Records are prepared only. No detector is configured; this session does not assess traffic safety.",
    analysis_records: "Session connections",
    analysis_origin: "Source",
    analysis_no_records: "No connections were prepared in this session.",
    analysis_alerts: "Session alerts",
    analysis_error_records: "Invalid records or missing selected connections. The failed batch was not saved; earlier batches remain committed.",
    analysis_error_sensor: "Could not read the sensor. Previously imported batches remain saved; retry the operation.",
    analysis_error_conflict: "Read progress changed. Retry the operation.",
    analysis_error_detector: "Processing failed. The failed batch was not saved; earlier batches remain committed.",
    analysis_error_processing: "The session failed. Previously committed data remains saved; retry the operation.",
    analysis_error_restart: "The server restart interrupted this session. Start the operation again manually.",
    analysis_error_interrupted: "The request was interrupted. Start the operation again manually.",
    severity_CRITICAL: "Critical",
    severity_HIGH: "High",
    severity_MEDIUM: "Medium",
    severity_LOW: "Low",
    status_NEW: "New",
    status_ACKNOWLEDGED: "Acknowledged",
    status_RESOLVED: "Resolved",
    status_FALSE_POSITIVE: "False positive",
    proto_tcp: "TCP",
    proto_udp: "UDP",
    proto_icmp: "ICMP",
    state_SF: "SF (Normal)",
    state_S0: "S0 (No SYN-ACK)",
    state_REJ: "REJ (Rejected)",
    attack_ssh: "Repeated SSH attempts",
    attack_scan: "Port scan",
    attack_dos: "DoS / SYN Flood",
    attack_anomaly: "Statistical anomaly",
    chart_total: "Total",
    username_placeholder: "Username",

    // App & Layout
    app_title: "AI NIDS Portal",
    hub_title: "AI NIDS",
    nav_dashboard: "Live Dashboard",
    nav_connections: "Zeek Flows",
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
    btn_analyzing: "Analyzing flows...",
    btn_reset_sensor: "Reset sensor cursor",
    btn_resetting_sensor: "Resetting cursor...",
    btn_reset_db: "Reset DB",
    btn_clearing_db: "Clearing...",
    confirm_clear_db:
      "Are you sure you want to delete alerts, connections and analysis-session history?",
    analysis_done:
      "Analysis completed: {conns} new connections, {alerts} alerts detected.",

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
    no_alerts: "No alerts matching the current filter.",

    // Connections Page
    conn_title: "Zeek Network Flows (conn.log)",
    filter_all_protos: "All Protocols",
    btn_refresh: "Refresh",
    conn_history_title: "Recorded Session History",
    no_connections: "No connections recorded in the database.",
    th_uid: "UID",
    th_protocol: "Protocol",
    th_service: "Service",
    th_conn_state: "Conn State",
    th_duration: "Duration (s)",
    th_bytes: "Bytes (Orig / Resp)",
    th_packets: "Packets",

    // 404 Not Found Page
    not_found_title: "Page Not Found",
    not_found_desc:
      "The route you tried to access does not exist in the application.",
    not_found_back_dashboard: "Back to Dashboard",
    not_found_back_login: "Back to Sign In",

    // Charts & Analytics
    chart_attacks_title: "Detected Attack Vectors",
    chart_severity_title: "Threat Severity Matrix",
    chart_ip_title: "Top Attacking Sources (IP)",
    chart_no_data: "No data to display in chart",

    // Report Export
    btn_export_csv: "Export CSV",
    btn_export_json: "Export JSON",
    btn_exporting: "Downloading...",
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

export const I18nProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [language, setLanguageState] = useState<Language>(() => {
    const saved = localStorage.getItem(
      STORAGE_KEYS.LANGUAGE,
    ) as Language | null;
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

  useEffect(() => {
    document.documentElement.lang = language;
  }, [language]);

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

  const t = useCallback(
    (key: TranslationKey, params?: Record<string, string | number>): string => {
      const langDict = translations[language] || translations.ro;
      let text: string = langDict[key] || translations.ro[key] || key;
      if (params) {
        Object.entries(params).forEach(([paramKey, val]) => {
          text = text.replace(
            new RegExp(`\\{${paramKey}\\}`, "g"),
            String(val),
          );
        });
      }
      return text;
    },
    [language],
  );

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
