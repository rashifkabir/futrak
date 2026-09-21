import ScorePlate from '../components/ScorePlate';
import type { AssessmentState } from '../lib/data';

// Home: the score plate is empty until calibration + attempts exist.
// No fabricated rating, no fake "this week" data.
export default function Home({ assessment }: { assessment: AssessmentState }) {
  // shooting rating would aggregate calibrated cells — none exist yet, so null.
  const anyScored = Object.values(assessment).some(c => c.score !== null);
  const rating = anyScored ? null : null; // stays null: no calibrated scorer yet

  return (
    <>
      <div className="screen-hd">
        <div className="screen-eyebrow">Futra</div>
        <h1 className="screen-title">Your shooting</h1>
      </div>
      <div className="screen-pad">
        <ScorePlate value={rating} label="Shooting rating" sub={rating === null ? 'take your first assessment' : undefined} />

        <div className="sect-label">Next step</div>
        <div className="card">
          <div className="card-k">Get started</div>
          <div className="card-t">Film your first shot</div>
          <div className="card-d">Static laces to begin. One phone, side-on, slow-mo.</div>
          <div style={{ marginTop: 12 }}><span className="btn">Go to assess</span></div>
        </div>

        <div className="sect-label">This season</div>
        <div className="card">
          <div className="card-k">Ranking</div>
          <div className="card-t" style={{ color: 'var(--muted)' }}>— no rank yet</div>
          <div className="card-d">Complete an assessment to enter the ladder.</div>
        </div>
      </div>
    </>
  );
}
