import { AuthContext } from "./auth-context";
import {
  useEffect,
  useState,
  useCallback,
  useRef,
  type ReactNode,
} from "react";
import { api, ApiError, onSessionInvalid } from "@/services/api";
import type { User } from "@/services/types";
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [sessionExpired, setSessionExpired] = useState(false);
  const pending = useRef<AbortController | null>(null);
  const refreshUser = useCallback(async () => {
    pending.current?.abort();
    const controller = new AbortController();
    pending.current = controller;
    setLoading(true);
    setError(false);
    try {
      const current = await api.getMe(controller.signal);
      if (!controller.signal.aborted) setUser(current);
      return !controller.signal.aborted;
    } catch (err) {
      if (controller.signal.aborted) return false;
      if (err instanceof ApiError && (err.status === 401 || err.status === 403))
        setUser(null);
      else setError(true);
      return false;
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }, []);
  useEffect(() => {
    // Synchronize authentication with the server's HttpOnly cookie session.
    // oxlint-disable-next-line react/set-state-in-effect
    void refreshUser();
    return () => pending.current?.abort();
  }, [refreshUser]);
  useEffect(
    () =>
      onSessionInvalid(() => {
        if (user) setSessionExpired(true);
        setUser(null);
      }),
    [user],
  );
  const login = async (username: string, password: string) => {
    pending.current?.abort();
    setError(false);
    const result = await api.login(username, password);
    setUser(result.user);
    setError(false);
    setLoading(false);
    setSessionExpired(false);
  };
  const logout = async () => {
    await api.logout();
    setUser(null);
    setSessionExpired(false);
  };
  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        error,
        sessionExpired,
        login,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
