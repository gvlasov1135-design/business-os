import type { Metadata } from "next";

import { AppNav } from "@/components/app-nav";
import { TopBar } from "@/components/top-bar";

import "./globals.css";

export const metadata: Metadata = {
  title: "Business OS",
  description: "Вертикальный срез Business OS",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ru">
      <body>
        <div className="app-shell">
          <aside className="app-sidebar">
            <AppNav />
          </aside>
          <div className="app-main">
            <TopBar />
            <section className="app-content">{children}</section>
          </div>
        </div>
      </body>
    </html>
  );
}
