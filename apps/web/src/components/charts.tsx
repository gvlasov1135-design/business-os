export function BarChart({
  label,
  value,
  max = 10,
  color = "#f06a6a",
}: {
  label: string;
  value: number;
  max?: number;
  color?: string;
}) {
  const height = Math.max(8, Math.round((value / max) * 160));
  return (
    <svg viewBox="0 0 320 220" width="100%" height="200" role="img" aria-label={label}>
      {[0, 2, 4, 6, 8, 10].map((tick) => {
        const y = 180 - (tick / max) * 160;
        return (
          <g key={tick}>
            <line x1="40" y1={y} x2="300" y2={y} stroke="#eee" />
            <text x="28" y={y + 4} textAnchor="end" fontSize="11" fill="#6d6e6f">
              {tick}
            </text>
          </g>
        );
      })}
      <rect x="140" y={180 - height} width="48" height={height} rx="4" fill={color} />
      <text x="164" y="205" textAnchor="middle" fontSize="12" fill="#1e1f21">
        {label}
      </text>
      <text x="12" y="24" fontSize="11" fill="#6d6e6f">
        count
      </text>
    </svg>
  );
}

export function DonutChart({
  center,
  segments,
}: {
  center: string;
  segments: Array<{ value: number; color: string }>;
}) {
  const total = segments.reduce((sum, item) => sum + item.value, 0) || 1;
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  let offset = 0;

  return (
    <svg viewBox="0 0 160 160" width="160" height="160" role="img">
      <circle cx="80" cy="80" r={radius} fill="none" stroke="#edf0f2" strokeWidth="18" />
      {segments.map((segment, index) => {
        const length = (segment.value / total) * circumference;
        const dash = `${length} ${circumference - length}`;
        const node = (
          <circle
            key={`${segment.color}-${index}`}
            cx="80"
            cy="80"
            r={radius}
            fill="none"
            stroke={segment.color}
            strokeWidth="18"
            strokeDasharray={dash}
            strokeDashoffset={-offset}
            transform="rotate(-90 80 80)"
          />
        );
        offset += length;
        return node;
      })}
      <text x="80" y="86" textAnchor="middle" fontSize="28" fontWeight="700" fill="#1e1f21">
        {center}
      </text>
    </svg>
  );
}

export function DotChart({
  value,
  max = 10,
  color = "#a871e3",
}: {
  value: number;
  max?: number;
  color?: string;
}) {
  const y = 180 - (value / max) * 160;
  return (
    <svg viewBox="0 0 320 220" width="100%" height="200" role="img">
      {[0, 2, 4, 6, 8, 10].map((tick) => {
        const tickY = 180 - (tick / max) * 160;
        return (
          <g key={tick}>
            <line x1="40" y1={tickY} x2="300" y2={tickY} stroke="#eee" />
            <text x="28" y={tickY + 4} textAnchor="end" fontSize="11" fill="#6d6e6f">
              {tick}
            </text>
          </g>
        );
      })}
      <line x1="160" y1="20" x2="160" y2="180" stroke="#ddd" />
      <circle cx="160" cy={y} r="7" fill={color} />
      <text x="12" y="24" fontSize="11" fill="#6d6e6f">
        count
      </text>
    </svg>
  );
}
