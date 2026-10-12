import { I18nProvider } from "@/i18n";
import { AuthProvider } from "@/contexts/AuthContext";
import { ProtectedRoute } from "@/components/ProtectedRoute";

export default function App() {
  return (
    <I18nProvider>
      <AuthProvider>
        <ProtectedRoute />
      </AuthProvider>
    </I18nProvider>
  );
}
