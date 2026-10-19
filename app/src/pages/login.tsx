import { Label } from "@/components/ui/label";
import { ApiError } from "@/services/api";
import { errorKey } from "@/services/errors";
import type { TranslationKey } from "@/i18n";
import { useState, type FormEvent } from "react";
import { useNavigate } from "@/router";
import { ShieldCheck, Lock, User, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import { LoadingOrb } from "@/components/ui/loading-orb";
import { SettingsDropdown } from "@/components/ui/settings-dropdown";
import { useI18n } from "@/i18n";
import { useAuth } from "@/hooks/use-auth";

export default function LoginPage() {
  const navigate = useNavigate();
  const { t } = useI18n();
  const { login, sessionExpired } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<TranslationKey | null>(null);

  const handleLogin = async (e: FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setIsLoading(true);

    try {
      await login(username, password);
      navigate("/dashboard");
    } catch (err) {
      setErrorMessage(
        err instanceof ApiError && err.status === 401
          ? "login_error_default"
          : errorKey(err),
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center p-4 relative transition-colors duration-150">
      {/* Top right settings button */}
      <div className="absolute top-4 right-4">
        <SettingsDropdown />
      </div>

      <div className="w-full max-w-md space-y-6">
        <div className="text-center space-y-2">
          <div className="inline-flex p-3 rounded-2xl bg-primary/10 border border-primary text-primary mb-2">
            <ShieldCheck className="w-8 h-8" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            {t("app_title")}
          </h1>
        </div>

        <Card className="border-border bg-card/90 shadow-2xl">
          <CardHeader>
            <CardTitle className="text-center">
              {t("login_card_title")}
            </CardTitle>
          </CardHeader>
          <form onSubmit={handleLogin}>
            <CardContent className="space-y-4">
              {(errorMessage || sessionExpired) && (
                <div className="p-3 rounded-lg bg-destructive/10 border border-destructive/60 text-destructive text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span role="alert">
                    {t(errorMessage ?? "session_expired")}
                  </span>
                </div>
              )}

              <div className="space-y-2">
                <Label
                  htmlFor="username"
                  className="text-xs font-medium text-foreground flex items-center gap-1.5"
                >
                  <User className="w-3.5 h-3.5 text-muted-foreground" />
                  {t("login_username")}
                </Label>
                <Input
                  id="username"
                  autoComplete="username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder={t("username_placeholder")}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label
                  htmlFor="password"
                  className="text-xs font-medium text-foreground flex items-center gap-1.5"
                >
                  <Lock className="w-3.5 h-3.5 text-muted-foreground" />
                  {t("login_password")}
                </Label>
                <Input
                  id="password"
                  autoComplete="current-password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>
            </CardContent>

            <CardFooter className="pt-2">
              <Button
                type="submit"
                className="w-full h-10 gap-2 cursor-pointer"
                disabled={isLoading}
              >
                {isLoading ? (
                  <LoadingOrb
                    state="solving"
                    size={20}
                    text={t("login_verifying")}
                  />
                ) : (
                  <span>{t("login_button")}</span>
                )}
              </Button>
            </CardFooter>
          </form>
        </Card>
      </div>
    </div>
  );
}
