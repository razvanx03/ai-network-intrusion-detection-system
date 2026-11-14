import { Languages, Settings, SunMoon, Trash2 } from "lucide-react";
import { useState } from "react";
import { ResetDataDialog } from "@/components/reset-data-dialog";
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
  DropdownMenuItem,
} from "@/components/ui/dropdown-menu";
export function SettingsDropdown() {
  const { language, setLanguage, theme, setTheme, t } = useI18n();
  const [resetOpen, setResetOpen] = useState(false);
  return (
    <><DropdownMenu modal={false}>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="size-8 sm:size-10" aria-label={t("settings_title")}>
          <Settings className="size-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuLabel className="flex items-center gap-2"><Languages className="size-3.5" aria-hidden="true" />{t("settings_language")}</DropdownMenuLabel>
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
        <DropdownMenuLabel className="flex items-center gap-2"><SunMoon className="size-3.5" aria-hidden="true" />{t("settings_theme")}</DropdownMenuLabel>
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
        <DropdownMenuSeparator />
        <DropdownMenuItem className="text-destructive focus:text-destructive" onSelect={() => setResetOpen(true)}><Trash2 className="mr-2 size-4" />{t("reset_menu")}</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
    {resetOpen && <ResetDataDialog close={() => setResetOpen(false)} />}</>
  );
}
