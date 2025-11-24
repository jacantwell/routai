"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  ReactNode,
} from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface SessionContextType {
  sessionId: string | null;
  isLoading: boolean;
  error: string | null;
  createNewSession: () => Promise<void>;
}

const SessionContext = createContext<SessionContextType | undefined>(undefined);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const createNewSession = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      console.log("Creating new session...");
      const response = await fetch(`${API_URL}/sessions`, {
        method: "POST",
      });

      if (!response.ok) {
        throw new Error("Failed to create session");
      }

      const data = await response.json();
      const newSessionId = data.session_id;

      setSessionId(newSessionId);

      // Store in localStorage for persistence across refreshes
      if (typeof window !== "undefined") {
        localStorage.setItem("routai_session_id", newSessionId);
      }

      console.log("Session created:", newSessionId);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to create session";
      console.error("Error creating session:", err);
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    const initializeSession = async () => {
      console.log("Initializing session...");
      // ALWAYS create a new session on component mount (refresh or first load)
      await createNewSession();
    };

    initializeSession();
  }, [createNewSession]);

  return (
    <SessionContext.Provider
      value={{
        sessionId,
        isLoading,
        error,
        createNewSession,
      }}
    >
      {children}
    </SessionContext.Provider>
  );
}

export function useSession() {
  const context = useContext(SessionContext);

  if (context === undefined) {
    throw new Error("useSession must be used within a SessionProvider");
  }

  return context;
}
