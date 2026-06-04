"use client";

import { FormEvent, useEffect, useState } from "react";
import { KanbanBoard } from "@/components/KanbanBoard";
import { getToken, login, logout, register } from "@/lib/api";

type AuthMode = "login" | "register";

const USERNAME_PATTERN = /^[A-Za-z0-9_-]+$/;
const USERNAME_ERROR =
  "Username must be 3-32 characters: letters, numbers, _ or -.";
const PASSWORD_ERROR = "Password must be at least 8 characters.";

const validateRegistration = (username: string, password: string): string => {
  const trimmed = username.trim();
  if (trimmed.length < 3 || trimmed.length > 32 || !USERNAME_PATTERN.test(trimmed)) {
    return USERNAME_ERROR;
  }
  if (password.length < 8) {
    return PASSWORD_ERROR;
  }
  return "";
};

export const KanbanApp = () => {
  const [isReady, setIsReady] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [mode, setMode] = useState<AuthMode>("login");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    setIsAuthenticated(Boolean(getToken()));
    setIsReady(true);
  }, []);

  const isRegister = mode === "register";

  const switchMode = () => {
    setMode((current) => (current === "login" ? "register" : "login"));
    setError("");
    setPassword("");
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");

    if (isRegister) {
      const validationError = validateRegistration(username, password);
      if (validationError) {
        setError(validationError);
        return;
      }
    }

    setIsSubmitting(true);
    try {
      if (isRegister) {
        await register(username.trim(), password);
      } else {
        await login(username, password);
      }
      setIsAuthenticated(true);
      setPassword("");
    } catch (submitError) {
      if (isRegister) {
        setError(
          submitError instanceof Error ? submitError.message : "Could not create account."
        );
      } else {
        setError("Invalid credentials. Use user / password.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    setIsAuthenticated(false);
    setMode("login");
    setUsername("");
    setPassword("");
    setError("");
  };

  if (!isReady) {
    return null;
  }

  if (!isAuthenticated) {
    return (
      <main className="mx-auto flex min-h-screen w-full max-w-lg items-center px-6 py-10">
        <section className="w-full rounded-3xl border border-[var(--stroke)] bg-white p-8 shadow-[var(--shadow)]">
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-[var(--gray-text)]">
            Project Management MVP
          </p>
          <h1 className="mt-3 font-display text-3xl font-semibold text-[var(--navy-dark)]">
            {isRegister ? "Create account" : "Sign in"}
          </h1>
          <p className="mt-2 text-sm text-[var(--gray-text)]">
            {isRegister ? (
              "Choose a username and password to create your board."
            ) : (
              <>
                Use <strong>user</strong> and <strong>password</strong>, or create an account.
              </>
            )}
          </p>

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <label className="block text-sm font-medium text-[var(--navy-dark)]">
              Username
              <input
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                className="mt-2 w-full rounded-xl border border-[var(--stroke)] px-3 py-2 text-sm outline-none focus:border-[var(--primary-blue)]"
                autoComplete="username"
                required
              />
            </label>

            <label className="block text-sm font-medium text-[var(--navy-dark)]">
              Password
              <input
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                type="password"
                className="mt-2 w-full rounded-xl border border-[var(--stroke)] px-3 py-2 text-sm outline-none focus:border-[var(--primary-blue)]"
                autoComplete={isRegister ? "new-password" : "current-password"}
                required
              />
            </label>

            {error ? (
              <p role="alert" className="text-sm font-medium text-red-600">
                {error}
              </p>
            ) : null}

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full rounded-full bg-[var(--secondary-purple)] px-4 py-3 text-sm font-semibold uppercase tracking-wide text-white transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isSubmitting
                ? isRegister
                  ? "Creating account..."
                  : "Signing in..."
                : isRegister
                  ? "Create account"
                  : "Sign in"}
            </button>
          </form>

          <button
            type="button"
            onClick={switchMode}
            data-testid="auth-mode-toggle"
            className="mt-4 text-sm font-medium text-[var(--primary-blue)] underline-offset-2 hover:underline"
          >
            {isRegister ? "Back to sign in" : "Create an account"}
          </button>
        </section>
      </main>
    );
  }

  return <KanbanBoard onLogout={handleLogout} />;
};
