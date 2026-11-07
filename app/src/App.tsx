import { AuthProvider } from "@/contexts/AuthContext";
import { ProtectedRoute } from "@/components/ProtectedRoute";

export default function App() {
  return (
    <AuthProvider>
      <ProtectedRoute />
    </AuthProvider>
  );
}
