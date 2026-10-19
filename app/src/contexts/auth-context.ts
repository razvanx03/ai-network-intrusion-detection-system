import { createContext } from "react";
import type { User } from "@/services/types";
export interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  error: boolean;
  sessionExpired: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}
export const AuthContext = createContext<AuthContextType | null>(null);
