import { useState } from 'react';
import { RANKED_SHOT_TYPES, CONDITIONS, type AssessmentState } from '../lib/data';
import FilmGuide from './FilmGuide';
import './Assess.css';

// The main ranked assessment matrix — ranked shot types x 2 conditions.
// Trivela is deliberately excluded here (reserved for the £2.50
// side-competition path, see lib/shotTypes.ts) but its cell/scorer stay
// intact underneath; only this display is filtered.
// Cells show attempts + honest "—" for scores that don't exist yet.
export default function Assess({ assessment }: { assessment: AssessmentState }) {
  const [guide, setGuide] = useState(false);

  if (guide) return <FilmGuide onBack={() => setGuide(false)} />;

  return (
    <>
      <div className="screen-hd">
        <div className="screen-eyebrow">Assessment</div>
        <h1 className="screen-title">Shooting matrix</h1>
      </div>
      <div className="screen-pad">
        <div className="matrix">
          <div className="mx-row mx-head">
            <div className="mx-corner" />
            {CONDITIONS.map(c => (
              <div key={c.id} className="mx-cond">
                {c.name}
                <span>{c.measuresPower ? 'technique + power' : 'technique'}</span>
              </div>
            ))}
          </div>
          {RANKED_SHOT_TYPES.map(st => (
            <div key={st.id} className="mx-row">
              <div className={`mx-type mx-${st.id}`}>{st.name}</div>
              {CONDITIONS.map(c => {
                const cell = assessment[`${st.id}:${c.id}`];
                return (
                  <div key={c.id} className="mx-cell">
                    <div className="mx-score tabnum">{cell.score ?? '—'}</div>
                    <div className="mx-att">{cell.attempts}/{cell.baseAttempts} attempts</div>
                  </div>
                );
              })}
            </div>
          ))}
        </div>

        <div className="card" style={{ marginTop: 16 }}>
          <div className="card-k">Next up</div>
          <div className="card-t">Laces · Static</div>
          <div className="card-d">Still ball, side-on at ~90°, full body in frame. The scoring isn’t calibrated yet — this is where your shots will be measured once it is.</div>
          <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
            <button className="btn" onClick={() => setGuide(true)}>Film attempt</button>
            <span className="btn btn-ghost">+2 via ad / £1.50</span>
          </div>
        </div>

        <p className="mx-note">Static measures technique and power (still ball). Run-up measures technique only — a moving ball makes power unreliable.</p>
      </div>
    </>
  );
}
