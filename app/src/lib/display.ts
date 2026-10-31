import type { TranslationKey } from "@/i18n";
export const attackKeys: Record<string, TranslationKey> = {
  "Suspicious Connection": "finding_suspicious_connection",
  "SSH Brute-Force": "attack_ssh",
  "Port Scan": "attack_scan",
  "DoS / SYN Flood": "attack_dos",
  "Statistical Anomaly": "attack_anomaly",
};

export const descriptionKeys: Record<string, TranslationKey> = {
  connection_model_review: "finding_connection_review",
};
