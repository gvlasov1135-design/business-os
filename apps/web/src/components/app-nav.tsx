"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { getAccessToken, getAuthUser } from "@/lib/auth";

type NavLink = { href: string; label: string; glyph: string; hint: string };

type NavGroup = { title: string; links: NavLink[] };

const GROUPS: NavGroup[] = [
  {
    title: "Работа руководителя",
    links: [
      {
        href: "/reports",
        label: "Моя отчётность",
        glyph: "▦",
        hint: "Загрузить Excel → выводы",
      },
      {
        href: "/executive",
        label: "Кабинет",
        glyph: "▣",
        hint: "Готовность, SLA и решения",
      },
      {
        href: "/council",
        label: "Заседание",
        glyph: "◎",
        hint: "Общий стол и чаты с агентами",
      },
      {
        href: "/decisions",
        label: "Решения",
        glyph: "✓",
        hint: "Принятое и контрольные точки",
      },
      {
        href: "/kpi",
        label: "KPI",
        glyph: "▣",
        hint: "Формулы и фактические снимки",
      },
    ],
  },
  {
    title: "Данные и нормы",
    links: [
      {
        href: "/demo",
        label: "Демо",
        glyph: "▷",
        hint: "Полный прогон Sales SLA",
      },
      {
        href: "/documents",
        label: "Документы",
        glyph: "☰",
        hint: "Регламенты и утверждения",
      },
      {
        href: "/sources",
        label: "Источники",
        glyph: "⇢",
        hint: "CRM и импорт фактов",
      },
      {
        href: "/alignment",
        label: "Сверка",
        glyph: "◫",
        hint: "Норматив vs факт CRM",
      },
    ],
  },
  {
    title: "Качество",
    links: [
      {
        href: "/quality",
        label: "Качество",
        glyph: "⚠",
        hint: "DQ-проблемы и silent skip",
      },
      {
        href: "/resolution",
        label: "Сущности",
        glyph: "⚭",
        hint: "Дубликаты и объединение",
      },
      {
        href: "/knowledge",
        label: "Знания",
        glyph: "◈",
        hint: "Подтверждённые записи",
      },
    ],
  },
  {
    title: "Система",
    links: [
      {
        href: "/analysis",
        label: "Анализ",
        glyph: "▤",
        hint: "Разовый вопрос агентам",
      },
      {
        href: "/audit",
        label: "Аудит",
        glyph: "◉",
        hint: "Журнал действий",
      },
      {
        href: "/",
        label: "Главная",
        glyph: "⌂",
        hint: "Обзор пилота",
      },
    ],
  },
];

export function AppNav() {
  const pathname = usePathname();
  const [authed, setAuthed] = useState(false);

  useEffect(() => {
    setAuthed(Boolean(getAccessToken() && getAuthUser()));
  }, [pathname]);

  return (
    <>
      <div className="sidebar-brand">
        <strong>business os</strong>
        <button className="sidebar-icon-btn" type="button" aria-label="Меню">
          ☰
        </button>
      </div>

      <nav>
        {!authed && (
          <div className="nav-group">
            <div className="nav-group-title">Доступ</div>
            <Link
              href="/login"
              title="Войти в пилот"
              aria-current={pathname === "/login" ? "page" : undefined}
            >
              <span className="nav-glyph">⌁</span>
              <span className="nav-label-wrap">
                <span className="nav-label">Вход</span>
                <span className="nav-hint">Сессия пилота</span>
              </span>
            </Link>
          </div>
        )}
        {GROUPS.map((group) => (
          <div className="nav-group" key={group.title}>
            <div className="nav-group-title">{group.title}</div>
            {group.links.map((link) => {
              const active =
                link.href === "/"
                  ? pathname === "/"
                  : pathname === link.href || pathname.startsWith(`${link.href}/`);
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  title={link.hint}
                  aria-current={active ? "page" : undefined}
                >
                  <span className="nav-glyph">{link.glyph}</span>
                  <span className="nav-label-wrap">
                    <span className="nav-label">{link.label}</span>
                    <span className="nav-hint">{link.hint}</span>
                  </span>
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      <div className="sidebar-section">
        <h3>Цикл руководителя</h3>
        <div className="sidebar-chip">Отчётность → Выводы → Решение → Кабинет</div>
      </div>

      <div className="sidebar-footer">
        <Link href="/reports">Загрузить отчётность</Link>
        <Link href="/council">Открыть заседание</Link>
        <Link href="/demo">Запустить демо-срез</Link>
        <Link href="/login">{authed ? "Сменить пользователя" : "Войти"}</Link>
      </div>
    </>
  );
}
