import { ATTRIBUTES } from '../lib/data';
import './Profile.css';

// Profile: shooting shown as the FIRST attribute (live), others visible
// but honestly locked as "coming" — so shooting reads as v1's attribute,
// not the only attribute the platform will ever have.
export default function Profile() {
  return (
    <>
      <div className="screen-hd">
        <div className="screen-eyebrow">Profile</div>
        <h1 className="screen-title">Player card</h1>
      </div>
      <div className="screen-pad">
        <div className="pcard">
          <div className="pcard-name">Set up your profile</div>
          <div className="pcard-meta">Position · foot · age band · location — added when you register.</div>
        </div>

        <div className="sect-label">Attributes</div>
        {ATTRIBUTES.map(a => (
          <div key={a.id} className={`attr ${a.status}`}>
            <div className="attr-name">{a.name}</div>
            {a.status === 'live'
              ? <div className="attr-val tabnum">—</div>
              : <div className="attr-lock">Coming</div>}
          </div>
        ))}
        <p className="attr-note">Shooting is the first attribute at launch. Finishing, pace and dribbling arrive in later releases.</p>

        <div className="sect-label">v1 products</div>
        <div className="card">
          <div className="card-k">Season pass</div>
          <div className="card-t">Adaptive plan + full breakdown</div>
          <div className="card-d">Deep analysis, extra attempts, status. Never gates competing or rewards.</div>
        </div>
        <div className="card">
          <div className="card-k">One-off</div>
          <div className="card-t">Verified Performance Portfolio</div>
          <div className="card-d">An official record of your measured scores and best clips. Framework calibrated with a UEFA-licensed coach.</div>
        </div>
      </div>
    </>
  );
}
