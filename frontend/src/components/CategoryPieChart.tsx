import { fmtCurrency } from "../utils/currency";

export interface CategoryPieChartSegment {
  key: string;
  label: string;
  value: number;
  color: string;
}

interface Props {
  segments: CategoryPieChartSegment[];
}

const SIZE = 140;
const CENTER = SIZE / 2;
const RADIUS = 52;
const STROKE_WIDTH = 24;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

/**
 * Hand-rolled SVG donut chart. Segments are drawn as stroked-circle arcs
 * (strokeDasharray/offset around the circumference) rather than <path> arc
 * commands — that avoids the degenerate "single 360-degree arc" case a
 * standard SVG arc path can't represent directly, so one category at 100%
 * just renders as a full ring with no special-casing.
 */
export function CategoryPieChart({ segments }: Props) {
  const total = segments.reduce((sum, s) => sum + s.value, 0);
  if (total <= 0) return null;

  const withLengths = segments.map((s) => {
    const fraction = s.value / total;
    return { ...s, fraction, length: fraction * CIRCUMFERENCE };
  });
  const arcs = withLengths.map((s, i) => {
    const offsetSoFar = withLengths.slice(0, i).reduce((sum, a) => sum + a.length, 0);
    return {
      ...s,
      dashArray: `${s.length} ${CIRCUMFERENCE - s.length}`,
      dashOffset: -offsetSoFar,
    };
  });

  const summary = arcs
    .map((a) => `${a.label} ${Math.round(a.fraction * 100)}%`)
    .join(", ");

  return (
    <div className="category-pie-chart">
      <svg
        viewBox={`0 0 ${SIZE} ${SIZE}`}
        className="category-pie-chart__svg"
        role="img"
        aria-label={`Annual cost by category: ${summary}`}
      >
        <g transform={`rotate(-90 ${CENTER} ${CENTER})`}>
          {arcs.map((a) => (
            <circle
              key={a.key}
              cx={CENTER}
              cy={CENTER}
              r={RADIUS}
              fill="none"
              stroke={a.color}
              strokeWidth={STROKE_WIDTH}
              strokeDasharray={a.dashArray}
              strokeDashoffset={a.dashOffset}
            />
          ))}
        </g>
      </svg>
      <ul className="category-pie-chart__legend">
        {arcs.map((a) => (
          <li key={a.key} className="category-pie-chart__legend-item">
            <span
              className="category-pie-chart__swatch"
              style={{ backgroundColor: a.color }}
              aria-hidden="true"
            />
            <span className="category-pie-chart__legend-label">{a.label}</span>
            <span className="category-pie-chart__legend-value">
              {fmtCurrency(a.value)} &middot; {Math.round(a.fraction * 100)}%
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
