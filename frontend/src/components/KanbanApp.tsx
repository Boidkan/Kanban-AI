"use client";

import { FormEvent, useEffect, useState } from "react";
import { KanbanBoard } from "@/components/KanbanBoard";
import { getToken, login, logout } from "@/lib/api";

export const KanbanApp = () => {
  const [isReady, setIsReady] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    setIsAuthenticated(Boolean(getToken()));
    setIsReady(true);
  }, []);

  const handleLogin = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSubmitting(true);
    setError("");

    try {
      await login(username, password);
      setIsAuthenticated(true);
      setPassword("");
    } catch {
      setError("Invalid credentials. Use user / password.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    setIsAuthenticated(false);
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
            Sign in
          </h1>
          <p className="mt-2 text-sm text-[var(--gray-text)]">
            Use <strong>user</strong> and <strong>password</strong>.
          </p>

          <form onSubmit={handleLogin} className="mt-6 space-y-4">
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
                autoComplete="current-password"
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
              {isSubmitting ? "Signing in..." : "Sign in"}
            </button>
          </form>
        </section>
      </main>
    );
  }

  return <KanbanBoard onLogout={handleLogout} />;
};
