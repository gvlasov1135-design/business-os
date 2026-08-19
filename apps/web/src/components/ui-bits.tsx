import type { ReactNode } from "react";
import Link from "next/link";

export function EmptyDemoHint() {
  return (
    <section className="panel">
      <h2>Пока нет данных демо</h2>
      <p>Сначала запустите вертикальный сценарий — появятся документ, сверка, AI и решение.</p>
      <p style={{ marginTop: 12 }}>
        <Link href="/demo" className="btn btn-primary">
          Открыть демо
        </Link>
      </p>
    </section>
  );
}

export function StatusPill({ value }: { value: string }) {
  const tone =
    value.includes("confirm") ||
    value === "ready" ||
    value === "accepted" ||
    value === "accepted_deviation" ||
    value === "stored" ||
    value === "met" ||
    value === "active"
      ? "ok"
      : value.includes("reject") || value === "blocked" || value === "error" || value === "missed"
        ? "down"
        : "degraded";
  return <span className={tone}>{value}</span>;
}

export function FieldGrid({
  items,
}: {
  items: Array<{ label: string; value: ReactNode }>;
}) {
  return (
    <div className="field-grid">
      {items.map((item) => (
        <div key={item.label} className="field-item">
          <div className="field-label">{item.label}</div>
          <div className="field-value">{item.value}</div>
        </div>
      ))}
    </div>
  );
}

export function QuoteBlock({ text }: { text: string }) {
  return <blockquote className="quote-block">{text}</blockquote>;
}
