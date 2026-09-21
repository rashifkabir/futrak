import { useState } from 'react';
import './FilmGuide.css';

type Side = 'kicking' | 'planting';

// Trivela is filmed from the OPPOSITE side to laces/finesse (see project design notes) —
// the wrap-around swing only shows up as visible in-frame motion from the
// planting-foot side. This toggle exists so that exception is never silently
// flattened into one generic "stand here" diagram.
const SIDE_LABEL: Record<Side, string> = { kicking: 'kicking-foot', planting: 'planting-foot' };

export default function FilmGuide({ onBack }: { onBack: () => void }) {
  const [side, setSide] = useState<Side>('kicking');
  const sign = side === 'kicking' ? 1 : -1;
  const camX = 160 + sign * 95;

  return (
    <>
      <div className="screen-hd">
        <button className="fg-back" onClick={onBack}>‹ Back to Assess</button>
        <div className="screen-eyebrow">Camera setup</div>
        <h1 className="screen-title">How to film your shot</h1>
      </div>
      <div className="screen-pad">
        <div className="tabs">
          <button className={`tab ${side === 'kicking' ? 'on' : ''}`} onClick={() => setSide('kicking')}>Laces / Finesse</button>
          <button className={`tab ${side === 'planting' ? 'on' : ''}`} onClick={() => setSide('planting')}>Trivela</button>
        </div>

        <div className="sect-label">Camera position (bird's-eye view)</div>
        <div className="card fg-diagram-card">
          <svg viewBox="0 0 320 210" className="fg-svg">
            {/* shooting line */}
            <line x1="160" y1="185" x2="160" y2="28" stroke="var(--line)" strokeWidth="2" strokeDasharray="4 4" />
            <path d="M154,36 L160,24 L166,36 Z" fill="var(--muted)" />
            <text x="160" y="16" textAnchor="middle" className="fg-lbl">shooting direction</text>

            {/* player */}
            <circle cx="160" cy="175" r="9" fill="var(--chalk)" />
            <text x="160" y="197" textAnchor="middle" className="fg-lbl">you</text>

            {/* ball */}
            <circle cx="160" cy="110" r="6" fill="var(--paint)" />
            <text x={160 - sign * 22} y="114" textAnchor="middle" className="fg-lbl">ball</text>

            {/* sightline to camera */}
            <line x1="170" y1="110" x2={camX - sign * 14} y2="110" stroke="var(--line)" strokeWidth="1.5" strokeDasharray="3 3" />
            <text x={(160 + camX) / 2} y="102" textAnchor="middle" className="fg-lbl">~3–4m</text>

            {/* right-angle marker */}
            <path d={`M160,100 L${160 + sign * 10},100 L${160 + sign * 10},110`} fill="none" stroke="var(--muted)" strokeWidth="1.5" />
            <text x={160 + sign * 16} y="96" textAnchor={sign > 0 ? 'start' : 'end'} className="fg-lbl fg-lbl-accent">90°</text>

            {/* camera */}
            <rect x={camX - 9} y="96" width="18" height="28" rx="4" fill="var(--turf3)" stroke="var(--chalk)" strokeWidth="1.5" />
            <circle cx={camX} cy="110" r="3.2" fill="var(--paint)" />
            <text x={camX} y="140" textAnchor="middle" className="fg-lbl">camera</text>
            <text x={camX} y="152" textAnchor="middle" className="fg-lbl fg-lbl-accent">{SIDE_LABEL[side]} side</text>
          </svg>
          <p className="fg-caption">
            {side === 'kicking'
              ? 'Laces and finesse: camera side-on, 90° to your shot, on your kicking-foot side.'
              : 'Trivela: camera on your planting-foot side — the opposite of laces and finesse. The wrap-around swing only reads clearly from here.'}
          </p>
          <p className="fg-tip">
            <strong>Line up to where the ball is actually going</strong> — not your stance or run-up. Same rule whether the shot's straight ahead or angled across goal.
          </p>
        </div>

        <div className="card fg-diagram-card">
          <div className="fg-subhead">Shot angled across goal — same rule</div>
          <svg viewBox="0 0 320 280" className="fg-svg">
            {/* faint "straight ahead" reference, for contrast */}
            <line x1="100" y1="160" x2="100" y2="20" stroke="var(--muted)" strokeWidth="1.5" strokeDasharray="3 4" opacity="0.35" />
            <text x="100" y="14" textAnchor="middle" className="fg-lbl" opacity="0.55">straight ahead (not this)</text>

            {/* goal */}
            <path d="M200,80 L200,25 L260,25 L260,80" fill="none" stroke="var(--chalk)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
            <text x="230" y="18" textAnchor="middle" className="fg-lbl">goal</text>

            {/* actual shot line, diagonal */}
            <line x1="100" y1="160" x2="230" y2="50" stroke="var(--paint)" strokeWidth="2" />
            <path d="M230,50 L225.6,60.3 L219.1,52.6 Z" fill="var(--paint)" />
            <text x="156" y="94" textAnchor="middle" className="fg-lbl fg-lbl-accent">shot line</text>

            {/* right-angle marker */}
            <path d="M112.2,149.7 A16,16 0 0,1 110.3,172.2" fill="none" stroke="var(--muted)" strokeWidth="1.5" />
            <text x="128" y="162" textAnchor="middle" className="fg-lbl fg-lbl-accent">90°</text>

            {/* camera sightline — on the shooter's kicking-foot (right) side, same convention as above */}
            <line x1="109" y1="170.7" x2="152.4" y2="221.8" stroke="var(--line)" strokeWidth="1.5" strokeDasharray="3 3" />
            <text x="137" y="191" textAnchor="middle" className="fg-lbl">~3–4m</text>

            {/* ball */}
            <circle cx="100" cy="160" r="6" fill="var(--paint)" />
            <text x="76" y="164" textAnchor="middle" className="fg-lbl">ball</text>

            {/* camera */}
            <rect x="152.4" y="218.5" width="18" height="28" rx="4" fill="var(--turf3)" stroke="var(--chalk)" strokeWidth="1.5" />
            <circle cx="161.4" cy="232.5" r="3.2" fill="var(--paint)" />
            <text x="161" y="262" textAnchor="middle" className="fg-lbl">camera</text>
          </svg>
          <p className="fg-caption">
            The ball isn't lined up straight in front of the goal — the shot line runs diagonally. The camera still goes 90° to that diagonal, on the kicking-foot side, not to an assumed "straight ahead". (Mirror it for trivela, same as the diagram above.)
          </p>
        </div>

        <div className="sect-label">Steps</div>
        <ol className="steps">
          <li className="step">
            <span className="step-num">1</span>
            <span className="step-text">Place the ball near the centre of frame, not off to one side — it needs room to travel after you strike it.</span>
          </li>
          <li className="step">
            <span className="step-num">2</span>
            <span className="step-text">Stand the phone side-on, 90° to your shooting line, on your {SIDE_LABEL[side]} side.</span>
          </li>
          <li className="step">
            <span className="step-num">3</span>
            <span className="step-text">You don't need to be in frame for the whole clip — just be fully in shot for the 8–10 frames before you strike.</span>
          </li>
          <li className="step">
            <span className="step-num">4</span>
            <span className="step-text">Film in slow-mo — 240fps if your phone supports it.</span>
          </li>
        </ol>

        <div className="sect-label">Framing guide</div>
        <div className="fg-frames">
          <div className="fg-frame">
            <svg viewBox="0 0 100 170" className="fg-frame-svg">
              <rect x="4" y="4" width="92" height="162" rx="10" fill="none" stroke="var(--line)" strokeWidth="2" />
              <line x1="10" y1="140" x2="90" y2="140" stroke="var(--line2)" strokeWidth="1.5" />
              <line x1="18" y1="140" x2="40" y2="140" stroke="var(--muted)" strokeWidth="1.5" strokeDasharray="2 3" />
              <line x1="60" y1="140" x2="82" y2="140" stroke="var(--muted)" strokeWidth="1.5" strokeDasharray="2 3" />
              <path d="M18,140 L23,136 L23,144 Z" fill="var(--muted)" />
              <path d="M82,140 L77,136 L77,144 Z" fill="var(--muted)" />
              <circle cx="50" cy="140" r="8" fill="var(--paint)" />
            </svg>
            <div className="fg-frame-cap">
              <strong>Ball</strong> centred, with space either side to travel after contact.
            </div>
          </div>
          <div className="fg-frame">
            <svg viewBox="0 0 100 170" className="fg-frame-svg">
              <rect x="4" y="4" width="92" height="162" rx="10" fill="none" stroke="var(--line)" strokeWidth="2" />
              <line x1="10" y1="150" x2="90" y2="150" stroke="var(--line2)" strokeWidth="1.5" />
              <circle cx="45" cy="25" r="9" fill="var(--chalk)" />
              <path d="M45,34 L51,80 L39,80 Z" fill="var(--chalk)" />
              <path d="M42,45 L20,55" stroke="var(--chalk)" strokeWidth="4" strokeLinecap="round" />
              <path d="M48,45 L64,34" stroke="var(--chalk)" strokeWidth="4" strokeLinecap="round" />
              <path d="M43,80 L35,150" stroke="var(--chalk)" strokeWidth="6" strokeLinecap="round" />
              <path d="M48,80 L70,100 L85,90" fill="none" stroke="var(--chalk)" strokeWidth="6" strokeLinecap="round" strokeLinejoin="round" />
              <circle cx="88" cy="88" r="6" fill="var(--paint)" />
            </svg>
            <div className="fg-frame-cap">
              <strong>You</strong>, fully in frame for the last 8–10 frames before contact.
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
