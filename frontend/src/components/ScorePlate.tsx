import './ScorePlate.css';

interface Props {
  value: number | null;
  label: string;
  sub?: string;
  size?: 'lg' | 'md' | 'sm';
}

// The signature element. When value is null the plate shows an honest
// empty state ("—" + reason) instead of a fabricated score.
export default function ScorePlate({ value, label, sub, size = 'lg' }: Props) {
  const empty = value === null;
  return (
    <div className={`plate plate-${size} ${empty ? 'plate-empty' : ''}`}>
      <div className="plate-num tabnum">{empty ? '—' : value}</div>
      <div className="plate-meta">
        <div className="plate-label">{label}</div>
        {sub && <div className="plate-sub">{sub}</div>}
        {empty && !sub && <div className="plate-sub">not yet measured</div>}
      </div>
    </div>
  );
}
