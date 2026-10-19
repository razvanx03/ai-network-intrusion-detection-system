import { useLocation } from "react-router-dom";
import { useNavigate } from "@/router";
import { ShieldOff, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { SettingsDropdown } from "@/components/ui/settings-dropdown";
import { useI18n } from "@/i18n";
import { useAuth } from "@/hooks/use-auth";

export default function NotFoundPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const { t } = useI18n();
  const { isAuthenticated } = useAuth();

  const handleBack = () => {
    if (isAuthenticated) {
      navigate("/dashboard");
    } else {
      navigate("/login");
    }
  };

  const content = (
    <Card className="w-full max-w-md border-border bg-card/90 shadow-2xl">
      <CardContent className="p-6 text-center space-y-5">
        <div className="flex flex-col items-center space-y-3">
          <div className="inline-flex p-3.5 rounded-2xl bg-critical/10 border border-critical/60 text-critical">
            <ShieldOff className="w-8 h-8" />
          </div>
          <Badge variant="critical" className="font-mono text-xs px-2.5 py-0.5">
            404
          </Badge>
        </div>

        <div className="space-y-1.5">
          <h1 className="text-xl font-bold tracking-tight text-foreground">
            {t("not_found_title")}
          </h1>
          <p className="text-xs text-muted-foreground leading-relaxed">
            {t("not_found_desc")}
          </p>
        </div>

        <div className="px-3 py-1.5 rounded-lg bg-background/80 border border-border inline-block max-w-full">
          <code className="text-xs font-mono text-muted-foreground break-all">
            {location.pathname}
          </code>
        </div>

        <div className="pt-1">
          <Button
            onClick={handleBack}
            className="w-full h-10 gap-2 bg-primary hover:bg-primary/90 text-primary-foreground cursor-pointer"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>
              {isAuthenticated
                ? t("not_found_back_dashboard")
                : t("not_found_back_login")}
            </span>
          </Button>
        </div>
      </CardContent>
    </Card>
  );

  if (isAuthenticated) {
    return (
      <div className="flex flex-col items-center justify-center py-20 px-4">
        {content}
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center p-4 relative transition-colors duration-150">
      <div className="absolute top-4 right-4">
        <SettingsDropdown />
      </div>
      {content}
    </div>
  );
}
