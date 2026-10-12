import React, { useState, useRef, useEffect } from "react";
import { Settings, Globe, Moon, Sun, Check } from "lucide-react";
import { useI18n } from "@/i18n";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export const SettingsDropdown: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const { language, setLanguage, theme, setTheme, t } = useI18n();

  // Close when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div ref={containerRef} className="relative inline-block text-left">
      <Button
        variant="ghost"
        size="sm"
        onClick={() => setIsOpen((prev) => !prev)}
        className={cn(
          "h-8 w-8 p-0 text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors",
          isOpen && "text-blue-400 bg-slate-800"
        )}
        title={t("settings_title")}
      >
        <Settings className={cn("w-4 h-4 transition-transform duration-200", isOpen && "rotate-45 text-blue-400")} />
      </Button>

      {isOpen && (
        <div className="absolute right-0 z-50 mt-2 w-60 rounded-xl border border-slate-800 bg-slate-900/95 backdrop-blur-md shadow-2xl p-3 text-xs space-y-3">
          {/* Main Title */}
          <div className="pb-1.5 border-b border-slate-800 text-slate-400 font-bold uppercase tracking-widest text-[10px]">
            {t("settings_title")}
          </div>

          {/* Language Section */}
          <div className="space-y-1.5">
            <div className="px-1 text-[10px] font-bold uppercase tracking-wider text-slate-500">
              {t("settings_language")}
            </div>
            <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-1 space-y-1">
              <button
                type="button"
                onClick={() => setLanguage("ro")}
                className={cn(
                  "w-full flex items-center justify-between px-2.5 py-1.5 rounded-md transition-colors cursor-pointer",
                  language === "ro"
                    ? "bg-blue-600/15 text-blue-400 font-semibold border border-blue-500/30 shadow-xs"
                    : "text-slate-300 hover:bg-slate-800/60 hover:text-slate-100 border border-transparent"
                )}
              >
                <div className="flex items-center gap-2">
                  <Globe className="w-3.5 h-3.5 shrink-0 text-blue-400" />
                  <span>{t("lang_ro")}</span>
                </div>
                {language === "ro" && <Check className="w-3.5 h-3.5 text-blue-400 shrink-0" />}
              </button>

              <button
                type="button"
                onClick={() => setLanguage("en")}
                className={cn(
                  "w-full flex items-center justify-between px-2.5 py-1.5 rounded-md transition-colors cursor-pointer",
                  language === "en"
                    ? "bg-blue-600/15 text-blue-400 font-semibold border border-blue-500/30 shadow-xs"
                    : "text-slate-300 hover:bg-slate-800/60 hover:text-slate-100 border border-transparent"
                )}
              >
                <div className="flex items-center gap-2">
                  <Globe className="w-3.5 h-3.5 shrink-0 text-blue-400" />
                  <span>{t("lang_en")}</span>
                </div>
                {language === "en" && <Check className="w-3.5 h-3.5 text-blue-400 shrink-0" />}
              </button>
            </div>
          </div>

          {/* Theme Section */}
          <div className="space-y-1.5">
            <div className="px-1 text-[10px] font-bold uppercase tracking-wider text-slate-500">
              {t("settings_theme")}
            </div>
            <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-1 space-y-1">
              <button
                type="button"
                onClick={() => setTheme("dark")}
                className={cn(
                  "w-full flex items-center justify-between px-2.5 py-1.5 rounded-md transition-colors cursor-pointer",
                  theme === "dark"
                    ? "bg-blue-600/15 text-blue-400 font-semibold border border-blue-500/30 shadow-xs"
                    : "text-slate-300 hover:bg-slate-800/60 hover:text-slate-100 border border-transparent"
                )}
              >
                <div className="flex items-center gap-2">
                  <Moon className="w-3.5 h-3.5 shrink-0 text-indigo-400" />
                  <span>{t("theme_dark")}</span>
                </div>
                {theme === "dark" && <Check className="w-3.5 h-3.5 text-blue-400 shrink-0" />}
              </button>

              <button
                type="button"
                onClick={() => setTheme("light")}
                className={cn(
                  "w-full flex items-center justify-between px-2.5 py-1.5 rounded-md transition-colors cursor-pointer",
                  theme === "light"
                    ? "bg-blue-600/15 text-blue-400 font-semibold border border-blue-500/30 shadow-xs"
                    : "text-slate-300 hover:bg-slate-800/60 hover:text-slate-100 border border-transparent"
                )}
              >
                <div className="flex items-center gap-2">
                  <Sun className="w-3.5 h-3.5 shrink-0 text-amber-400" />
                  <span>{t("theme_light")}</span>
                </div>
                {theme === "light" && <Check className="w-3.5 h-3.5 text-blue-400 shrink-0" />}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
