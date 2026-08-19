"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { bootstrapIdentity, login } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("admin@example.com");
  const [password, setPassword] = useState("demo-admin");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setInfo(null);
    try {
      await login(email, password);
      router.push("/demo");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось войти");
    } finally {
      setLoading(false);
    }
  }

  async function onBootstrap() {
    setLoading(true);
    setError(null);
    setInfo(null);
    try {
      const data = await bootstrapIdentity();
      setInfo(
        `Создано: ${data.company.name}. Войдите как ${data.user.email} / demo-admin (или BOOTSTRAP_ADMIN_PASSWORD).`,
      );
      setEmail(data.user.email);
      setPassword("demo-admin");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось выполнить bootstrap");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <div className="page-head" style={{ marginBottom: 16 }}>
        <h1>Вход</h1>
        <p>Локальная авторизация. Пароль задаётся при bootstrap (см. BOOTSTRAP_ADMIN_PASSWORD).</p>
      </div>

      <section className="panel" style={{ maxWidth: 480 }}>
        <form onSubmit={onSubmit} className="stack-form">
          <label>
            Email
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="username"
            />
          </label>
          <label>
            Пароль
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
          </label>
          {error && <p className="error-text">{error}</p>}
          {info && <p className="ok-text">{info}</p>}
          <div className="form-actions">
            <button className="btn btn-primary" type="submit" disabled={loading}>
              {loading ? "Работаю…" : "Войти"}
            </button>
            <button className="btn" type="button" onClick={onBootstrap} disabled={loading}>
              Создать демо-компанию
            </button>
          </div>
        </form>
      </section>
    </main>
  );
}
