"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { clearAuthSession, getAuthUser, type AuthUser } from "@/lib/auth";

export function TopBar({
  section = "Отчётность",
  title = "Операционная панель",
}: {
  section?: string;
  title?: string;
}) {
  const [user, setUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    setUser(getAuthUser());
  }, []);

  function onSignOut() {
    clearAuthSession();
    setUser(null);
    window.location.href = "/login";
  }

  return (
    <header className="topbar">
      <div className="topbar-left">
        <div className="crumb">
          {section} &gt; <strong>{title}</strong>
        </div>
        <span className="star" aria-hidden>
          ★
        </span>
      </div>
      <div className="topbar-right">
        {user ? (
          <span className="trial-pill" title={user.email}>
            {user.full_name}
          </span>
        ) : (
          <Link href="/login" className="trial-pill">
            Войти
          </Link>
        )}
        <div className="avatar-stack" aria-hidden>
          <span className="avatar">{(user?.full_name?.[0] ?? "B").toUpperCase()}</span>
        </div>
        {user ? (
          <button className="btn" type="button" onClick={onSignOut}>
            Выйти
          </button>
        ) : (
          <Link href="/login" className="btn">
            Вход
          </Link>
        )}
        <Link href="/council" className="btn-plus" aria-label="Заседание агентов" title="Заседание">
          +
        </Link>
        <span className="trial-pill">Пилот: заседание агентов</span>
      </div>
    </header>
  );
}
