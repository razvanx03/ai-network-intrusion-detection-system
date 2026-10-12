import React from "react";
import { Outlet, useLocation, Navigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { LoadingOrb } from "@/components/ui/loading-orb";
import AppLayout from "@/layouts/AppLayout";

const PROTECTED_PATHS = ["/dashboard", "/connections"];

export const ProtectedRoute: React.FC = () => {
  const location = useLocation();
  const { isAuthenticated, isLoading } = useAuth();
  const isLoginPage = location.pathname === "/login";
  const isProtectedPath = PROTECTED_PATHS.includes(location.pathname);

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

  // Unknown route (404 Not Found): render inside AppLayout if logged in, or standalone if logged out
  if (!isProtectedPath) {
    if (isAuthenticated) {
      return (
        <AppLayout>
          <Outlet />
        </AppLayout>
      );
    }
    return <Outlet />;
  }

  // Known protected route when not authenticated -> redirect to /login
  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  // Authenticated on protected route -> wrap page in main AppLayout
  return (
    <AppLayout>
      <Outlet />
    </AppLayout>
  );
};
