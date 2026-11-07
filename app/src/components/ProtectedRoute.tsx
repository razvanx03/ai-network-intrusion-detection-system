import { DataState } from "@/components/data-state";
import { ApiError } from "@/services/api";
import React from "react";
import { Outlet, useLocation, Navigate } from "react-router-dom";
import { useAuth } from "@/hooks/use-auth";
import { LoadingOrb } from "@/components/ui/loading-orb";
import AppLayout from "@/layouts/AppLayout";

const PROTECTED_PATHS = ["/dashboard", "/connections", "/all-data"];

export const ProtectedRoute: React.FC = () => {
  const location = useLocation();
  const { isAuthenticated, isLoading, error, refreshUser } = useAuth();
  const isLoginPage = location.pathname === "/login";
  const isProtectedPath = PROTECTED_PATHS.includes(location.pathname);

  // Redirect root / directly to /dashboard
  if (location.pathname === "/") {
    return <Navigate to="/dashboard" replace />;
  }

  // Active session check in progress
  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <LoadingOrb state="solving" size={32} />
      </div>
    );
  }

  // Resolve the cookie session before displaying the login form.
  if (isLoginPage) {
    if (isAuthenticated) return <Navigate to="/dashboard" replace />;
    return <Outlet />;
  }

  if (error)
    return (
      <div className="mx-auto max-w-xl p-6">
        <DataState
          loading={false}
          error={new ApiError(0)}
          hasData={false}
          retry={() => {
            void refreshUser();
          }}
        />
      </div>
    );

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
