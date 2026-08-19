interface ScoreDonutProps {
  score: number;
}

const HIGH_COLOR = "#0ca30c";
const LOW_COLOR = "#d03b3b";
const TRACK_COLOR = "#e1e0d9";
const THRESHOLD = 0.5;

const SIZE = 96;
const STROKE_WIDTH = 14;
const RADIUS = (SIZE - STROKE_WIDTH) / 2;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

export function ScoreDonut({ score }: ScoreDonutProps) {
  const clamped = Math.max(0, Math.min(1, score));
  const color = clamped >= THRESHOLD ? HIGH_COLOR : LOW_COLOR;
  const dash = CIRCUMFERENCE * clamped;

  return (
    <svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`} className="score-donut">
      <circle cx={SIZE / 2} cy={SIZE / 2} r={RADIUS} fill="none" stroke={TRACK_COLOR} strokeWidth={STROKE_WIDTH} />
      <circle
        cx={SIZE / 2}
        cy={SIZE / 2}
        r={RADIUS}
        fill="none"
        stroke={color}
        strokeWidth={STROKE_WIDTH}
        strokeDasharray={`${dash} ${CIRCUMFERENCE - dash}`}
        strokeLinecap="round"
        transform={`rotate(-90 ${SIZE / 2} ${SIZE / 2})`}
      />
      <text x="50%" y="50%" textAnchor="middle" dominantBaseline="central" className="score-donut-text">
        {clamped.toFixed(2)}
      </text>
    </svg>
  );
}
