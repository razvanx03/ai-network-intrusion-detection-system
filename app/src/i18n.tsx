/* oxlint-disable react/only-export-components -- Project policy keeps translations and their reactive provider in this single module. */
import React, {
  useContext,
  useState,
  useEffect,
  useCallback,
} from "react";
import { STORAGE_KEYS } from "@/constants";
import { I18nContext, type I18nContextType } from "@/contexts/i18n-context";

export type Language = "ro" | "en";
export type Theme = "dark" | "light";

export const translations = {
  ro: {
    analysis_busy: "Exista o analiza in curs. Asteapta finalizarea ei.",
    analysis_show_details: "Vezi conexiunile si constatarile sesiunii",
    analysis_hide_details: "Ascunde detaliile sesiunii",
    alert_status_updated: "Starea constatarii a fost actualizata.",
    page_loading: "Se incarca datele",
    stats_analyzed: "Conexiuni analizate de AI",
    stats_pending: "{count} in asteptarea analizei",
    stats_flagged: "Conexiuni semnalate",
    stats_review_pending: "{count} constatari de verificat",
    stats_sessions: "Sesiuni de analiza",
    stats_session_breakdown: "{completed} finalizate / {failed} esuate sau intrerupte",
    model_random_forest: "Random Forest",
    finding_origin: "Originea constatarilor",
    findings_model: "Constatari AI",
    findings_false_positive_count: "Marcate manual ca fals pozitiv: {count}",
    model_score: "Scor model",
    model_score_help: "Scorul exprima rezultatul clasificatorului, nu o probabilitate calibrata ca exista un atac.",
    finding_inspect: "Constatarea #{id}",
    finding_details: "Detalii",
    finding_change_status: "Schimba starea constatarii #{id}",
    finding_time: "Momentul conexiunii",
    finding_evidence: "Conexiuni sursa",
    finding_legacy_evidence: "Istoricul demonstrativ nu are conexiuni sursa asociate unei analize.",
    chart_protocols_title: "Conexiuni dupa protocol",
    stored_analysis_done: "Au fost analizate {count} conexiuni salvate; {alerts} constatari. Vezi istoricul din dashboard.",
    clear_selection: "Goleste selectia",
    select_page: "Selecteaza pagina",
    analyze_selection: "Analizeaza selectia ({count})",
    selection: "Selectie",
    select_connection: "Selecteaza conexiunea {uid}",
    selected: "Selectata",
    select: "Selecteaza",
    analysis_no_findings: "Modelul nu a emis constatari pentru aceasta sesiune.",
    analysis_no_new_connections: "Nu au fost gasite conexiuni noi de analizat.",
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
    cancel: "Anuleaza",
    clear_title: "Sterge datele locale?",
    close: "Inchide",
    pagination_navigation: "Navigare intre pagini",
    pagination_rows: "Randuri pe pagina",
    pagination_page_size: "Randuri pe pagina: {count}",
    pagination_go_to: "Pagina {page}",
    pagination_more: "Alte pagini",
    navigation: "Navigatie principala",
    finding_suspicious_connection: "Conexiune suspecta",
    finding_connection_review: "Caracteristicile conexiunii seamana cu traficul etichetat ca atac. Necesita verificare; nu confirma un atac.",
    legacy_demo: "Istoric demonstrativ",
    legacy_demo_notice: "Istoricul demonstrativ ({count} alerte) este separat de statisticile AI.",
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
    analysis_imported: "Conexiuni noi",
    analysis_prepared_count: "Inregistrari pregatite",
    analysis_findings_count: "Alerte generate",
    analysis_started_at: "Inceputa la",
    analysis_finished_at: "Incheiata la",
    analysis_source_label: "Sursa datelor",
    analysis_model_label: "Model AI",
    analysis_duration: "Durata",
    analysis_seconds: "{seconds} s",
    analysis_no_detector: "Datele sunt doar pregatite. Nu este configurat un detector; aceasta sesiune nu evalueaza siguranta traficului.",
    analysis_records: "Conexiunile sesiunii",
    analysis_origin: "Sursa",
    analysis_no_records: "Nu au fost pregatite conexiuni in aceasta sesiune.",
    analysis_alerts: "Alertele sesiunii",
    analysis_error_records: "Date invalide sau conexiuni selectate inexistente. Lotul care a esuat nu a fost salvat; loturile anterioare raman salvate.",
    analysis_error_sensor: "Senzorul nu a putut fi citit. Loturile deja importate raman salvate; reincercati operatia.",
    analysis_done_with_skips: "Analiza finalizata cu avertismente: {conns} conexiuni noi, {alerts} alerte; {files} fisiere omise. Vezi detaliile din istoricul analizelor.",
    analysis_skipped_files: "Fisiere omise: {count}",
    analysis_file_corrupt: "Date corupte sau invalide",
    analysis_file_unreadable: "Fisierul nu poate fi citit",
    analysis_file_oversized: "Inregistrare peste limita admisa",
    analysis_file_unavailable: "Fisier indisponibil la citire",
    analysis_skip_offset: "Citire omisa de la pozitia {offset}.",
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
    status_ACKNOWLEDGED: "In investigare",
    status_RESOLVED: "Rezolvata",
    status_FALSE_POSITIVE: "Fals pozitiv",
    proto_tcp: "TCP",
    proto_udp: "UDP",
    proto_icmp: "ICMP",
    state_SF: "Incheiata normal",
    state_S0: "Fara SYN-ACK",
    state_REJ: "Respins",
    attack_ssh: "Tentative repetate SSH",
    attack_scan: "Scanare de porturi",
    attack_dos: "DoS / SYN Flood",
    attack_anomaly: "Anomalie statistica",
    chart_total: "Total",
    username_placeholder: "Nume utilizator",

    // App & Layout
    app_title: "AI NIDS Portal",
    hub_title: "AI NIDS",
    nav_dashboard: "Dashboard",
    nav_connections: "Zeek Flows",
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
    stats_connections: "Conexiuni salvate",
    stats_connections_sub: "Inregistrari preluate din loguri",

    // Dashboard Alerts Table
    feed_title: "Constatari si verificare",
    filter_all_severities: "Toate Severitatile",
    th_severity: "Severitate",
    th_attack_type: "Tip constatare",
    th_source: "Sursa",
    th_destination: "Destinatie",
    th_mitre: "MITRE ATT&CK",
    th_status: "Status",
    th_action: "Actiune",
    no_alerts: "Nu exista alerte pentru filtrul curent.",

    // Connections Page
    conn_title: "Fluxuri de Retea Zeek (conn.log)",
    filter_all_protos: "Toate Protocoalele",
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
    chart_severity_title: "Constatari dupa severitate",
    chart_ip_title: "Surse cu cele mai multe constatari",
    chart_no_data: "Nu exista date de afisat in grafic",

    // Report Export
    btn_export_csv: "Export CSV",
    btn_export_json: "Export JSON",
    btn_exporting: "Se descarca...",
  },
  en: {
    analysis_busy: "An analysis is already running. Wait for it to finish.",
    analysis_show_details: "View session connections and findings",
    analysis_hide_details: "Hide session details",
    alert_status_updated: "Finding status updated.",
    page_loading: "Loading data",
    stats_analyzed: "AI-analyzed connections",
    stats_pending: "{count} awaiting analysis",
    stats_flagged: "Flagged connections",
    stats_review_pending: "{count} findings awaiting review",
    stats_sessions: "Analysis sessions",
    stats_session_breakdown: "{completed} completed / {failed} failed or interrupted",
    model_random_forest: "Random Forest",
    finding_origin: "Finding origin",
    findings_model: "AI findings",
    findings_false_positive_count: "Manually marked as false positive: {count}",
    model_score: "Model score",
    model_score_help: "The score is the classifier output, not a calibrated probability of an attack.",
    finding_inspect: "Finding #{id}",
    finding_details: "Details",
    finding_change_status: "Change status of finding #{id}",
    finding_time: "Connection time",
    finding_evidence: "Source connections",
    finding_legacy_evidence: "Demo history has no source connections associated with an analysis.",
    chart_protocols_title: "Connections by protocol",
    stored_analysis_done: "Analyzed {count} stored connections; {alerts} findings. View the session in the dashboard.",
    clear_selection: "Clear selection",
    select_page: "Select page",
    analyze_selection: "Analyze selection ({count})",
    selection: "Selection",
    select_connection: "Select connection {uid}",
    selected: "Selected",
    select: "Select",
    analysis_no_findings: "The model emitted no findings for this session.",
    analysis_no_new_connections: "No new connections were found to analyze.",
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
    cancel: "Cancel",
    clear_title: "Delete local data?",
    close: "Close",
    pagination_navigation: "Page navigation",
    pagination_rows: "Rows per page",
    pagination_page_size: "Rows per page: {count}",
    pagination_go_to: "Page {page}",
    pagination_more: "More pages",
    navigation: "Main navigation",
    finding_suspicious_connection: "Suspicious connection",
    finding_connection_review: "Connection characteristics resemble traffic labelled as attacks. Review is required; this does not confirm an attack.",
    legacy_demo: "Demo history",
    legacy_demo_notice: "Demo history ({count} alerts) is separate from AI statistics.",
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
    analysis_imported: "New connections",
    analysis_prepared_count: "Records prepared",
    analysis_findings_count: "Alerts generated",
    analysis_started_at: "Started at",
    analysis_finished_at: "Finished at",
    analysis_source_label: "Data source",
    analysis_model_label: "AI model",
    analysis_duration: "Duration",
    analysis_seconds: "{seconds} s",
    analysis_no_detector: "Records are prepared only. No detector is configured; this session does not assess traffic safety.",
    analysis_records: "Session connections",
    analysis_origin: "Source",
    analysis_no_records: "No connections were prepared in this session.",
    analysis_alerts: "Session alerts",
    analysis_error_records: "Invalid records or missing selected connections. The failed batch was not saved; earlier batches remain committed.",
    analysis_error_sensor: "Could not read the sensor. Previously imported batches remain saved; retry the operation.",
    analysis_done_with_skips: "Analysis completed with warnings: {conns} new connections, {alerts} alerts; {files} files skipped. See the analysis history for details.",
    analysis_skipped_files: "Skipped files: {count}",
    analysis_file_corrupt: "Corrupt or invalid data",
    analysis_file_unreadable: "File cannot be read",
    analysis_file_oversized: "Record exceeds the allowed limit",
    analysis_file_unavailable: "File unavailable during reading",
    analysis_skip_offset: "Reading skipped from position {offset}.",
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
    state_SF: "Normal closure",
    state_S0: "No SYN-ACK",
    state_REJ: "Rejected",
    attack_ssh: "Repeated SSH attempts",
    attack_scan: "Port scan",
    attack_dos: "DoS / SYN Flood",
    attack_anomaly: "Statistical anomaly",
    chart_total: "Total",
    username_placeholder: "Username",

    // App & Layout
    app_title: "AI NIDS Portal",
    hub_title: "AI NIDS",
    nav_dashboard: "Dashboard",
    nav_connections: "Zeek Flows",
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
    stats_connections: "Stored connections",
    stats_connections_sub: "Records imported from logs",

    // Dashboard Alerts Table
    feed_title: "Findings and review",
    filter_all_severities: "All Severities",
    th_severity: "Severity",
    th_attack_type: "Finding type",
    th_source: "Source",
    th_destination: "Destination",
    th_mitre: "MITRE ATT&CK",
    th_status: "Status",
    th_action: "Action",
    no_alerts: "No alerts matching the current filter.",

    // Connections Page
    conn_title: "Zeek Network Flows (conn.log)",
    filter_all_protos: "All Protocols",
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
    chart_severity_title: "Findings by severity",
    chart_ip_title: "Sources with the most findings",
    chart_no_data: "No data to display in chart",

    // Report Export
    btn_export_csv: "Export CSV",
    btn_export_json: "Export JSON",
    btn_exporting: "Downloading...",
  },
} as const;

export type TranslationKey = keyof typeof translations.ro;

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
