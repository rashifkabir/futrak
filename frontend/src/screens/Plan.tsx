import Empty from '../components/Empty';

// Adaptive plan (season pass). No weakness can be diagnosed until real
// assessments exist, so the plan is honestly empty, not pre-filled with
// fake drills.
export default function Plan() {
  return (
    <>
      <div className="screen-hd">
        <div className="screen-eyebrow">Adaptive plan · season pass</div>
        <h1 className="screen-title">Your plan</h1>
      </div>
      <div className="screen-pad">
        <Empty
          title="Nothing to work on yet"
          body="Once you’ve completed an assessment, your plan targets your weakest measured area, sets drills, and re-tests. It appears here after your first shots."
        />

        <div className="card" style={{ marginTop: 14 }}>
          <div className="card-k">What the pass unlocks</div>
          <div className="card-t">Plan + full breakdown</div>
          <div className="card-d">The adaptive drill path, frame-by-frame analysis of each strike, and deeper progress analytics. Competing and winning rewards never require the pass.</div>
          <div style={{ marginTop: 12 }}><span className="btn btn-ghost">See the pass</span></div>
        </div>
      </div>
    </>
  );
}
