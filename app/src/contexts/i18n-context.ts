import { createContext } from "react";
import type { Language, Theme, TranslationKey } from "@/i18n";

export interface I18nContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
  theme: Theme;
  setTheme: (theme: Theme) => void;
  t: (key: TranslationKey, params?: Record<string, string | number>) => string;
}

// Keep context identity independent of translation/provider hot updates.
export const I18nContext = createContext<I18nContextType | null>(null);
