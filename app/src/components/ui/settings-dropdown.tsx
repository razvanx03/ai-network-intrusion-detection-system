import { Settings } from "lucide-react";
import { useI18n } from "@/i18n";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
export function SettingsDropdown() {
  const { language, setLanguage, theme, setTheme, t } = useI18n();
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" aria-label={t("settings_title")}>
          <Settings className="size-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuLabel>{t("settings_language")}</DropdownMenuLabel>
        <DropdownMenuRadioGroup
          value={language}
          onValueChange={(value) => {
            if (value === "ro" || value === "en") setLanguage(value);
          }}
        >
          <DropdownMenuRadioItem value="ro">
            {t("lang_ro")}
          </DropdownMenuRadioItem>
          <DropdownMenuRadioItem value="en">
            {t("lang_en")}
          </DropdownMenuRadioItem>
        </DropdownMenuRadioGroup>
        <DropdownMenuSeparator />
        <DropdownMenuLabel>{t("settings_theme")}</DropdownMenuLabel>
        <DropdownMenuRadioGroup
          value={theme}
          onValueChange={(value) => {
            if (value === "dark" || value === "light") setTheme(value);
          }}
        >
          <DropdownMenuRadioItem value="dark">
            {t("theme_dark")}
          </DropdownMenuRadioItem>
          <DropdownMenuRadioItem value="light">
            {t("theme_light")}
          </DropdownMenuRadioItem>
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
