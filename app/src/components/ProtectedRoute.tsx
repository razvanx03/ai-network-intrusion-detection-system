import React from "react";
import { Outlet, useLocation, Navigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { LoadingOrb } from "@/components/ui/loading-orb";
import AppLayout from "@/layouts/AppLayout";

export const ProtectedRoute: React.FC = () => {
  const location = useLocation();
  const { isAuthenticated, isLoading } = useAuth();
  const isLoginPage = location.pathname === "/login";

  // Redirect root / directly to /dashboard
  if (location.pathname === "/") {
    return <Navigate to="/dashboard" replace />;
  }

  // Login page route
  if (isLoginPage) {
    if (!isLoading && isAuthenticated) {
      return <Navigate to="/dashboard" replace />;
    }
    return <Outlet />;
  }

  // Active session check in progress
  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <LoadingOrb state="solving" size={32} />
      </div>
    );
  }

  // Not authenticated -> redirect to /login
  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  // Authenticated -> wrap page in main AppLayout
  return (
    <AppLayout>
      <Outlet />
    </AppLayout>
  );
};
