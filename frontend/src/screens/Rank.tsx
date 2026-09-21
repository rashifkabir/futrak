import { useState } from 'react';
import { RANKED_SHOT_TYPES, LOCATIONS } from '../lib/data';
import Empty from '../components/Empty';
import './Rank.css';

// Leaderboards: Location x ranked Shot type. Genuinely empty — no fake
// players, no invented scores. Ladder populates once real assessments
// exist. Trivela is deliberately excluded (reserved for the £2.50
// side-competition path, see lib/shotTypes.ts), same as the Assess matrix.
export default function Rank() {
  const [loc, setLoc] = useState(0);
  const [st, setSt] = useState(0);

  return (
    <>
      <div className="screen-hd">
        <div className="screen-eyebrow">Season · leaderboards</div>
        <h1 className="screen-title">Rank</h1>
      </div>
      <div className="screen-pad">
        <div className="tabs">
          {LOCATIONS.map((l, i) => (
            <button key={l} className={`tab ${i === loc ? 'on' : ''}`} onClick={() => setLoc(i)}>{l}</button>
          ))}
        </div>
        <div className="tabs">
          {RANKED_SHOT_TYPES.map((s, i) => (
            <button key={s.id} className={`tab ${i === st ? 'on' : ''}`} onClick={() => setSt(i)}>{s.name.split(' ')[0]}</button>
          ))}
        </div>

        <div style={{ marginTop: 14 }}>
          <Empty
            title="No rankings yet"
            body={`The ${LOCATIONS[loc]} · ${RANKED_SHOT_TYPES[st].name} ladder fills once players complete verified assessments. Yours could be the first.`}
          />
        </div>

        <div className="card" style={{ marginTop: 14 }}>
          <div className="card-k">Monthly reward · top of the ladder</div>
          <div className="card-t">Session or remote analysis</div>
          <div className="card-d">London winners: a UEFA-coach group session. Outside London: bespoke remote analysis. Verification is free and required before month-end. Earned by skill — never bought.</div>
        </div>
      </div>
    </>
  );
}
