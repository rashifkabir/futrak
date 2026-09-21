import type React from 'react';
import { useState } from 'react';
import './components/Shell.css';
import { freshAssessment } from './lib/data';
import { IconHome, IconAssess, IconPitches, IconRank, IconPlan, IconProfile } from './components/icons';
import Home from './screens/Home';
import Assess from './screens/Assess';
import Pitches from './screens/Pitches';
import Rank from './screens/Rank';
import Plan from './screens/Plan';
import Profile from './screens/Profile';

type Tab = 'home' | 'assess' | 'pitches' | 'rank' | 'plan' | 'profile';

const NAV: { id: Tab; label: string; Icon: () => React.ReactElement }[] = [
  { id: 'home',    label: 'Home',    Icon: IconHome },
  { id: 'assess',  label: 'Assess',  Icon: IconAssess },
  { id: 'pitches', label: 'Pitches', Icon: IconPitches },
  { id: 'rank',    label: 'Rank',    Icon: IconRank },
  { id: 'plan',    label: 'Plan',    Icon: IconPlan },
  { id: 'profile', label: 'Profile', Icon: IconProfile },
];

export default function App() {
  const [tab, setTab] = useState<Tab>('home');
  const [assessment] = useState(freshAssessment());

  return (
    <div className="shell">
      <div className="shell-body">
        {tab === 'home' && <Home assessment={assessment} />}
        {tab === 'assess' && <Assess assessment={assessment} />}
        {tab === 'pitches' && <Pitches />}
        {tab === 'rank' && <Rank />}
        {tab === 'plan' && <Plan />}
        {tab === 'profile' && <Profile />}
      </div>
      <nav className="nav">
        {NAV.map(({ id, label, Icon }) => (
          <button key={id} className={tab === id ? 'on' : ''} onClick={() => setTab(id)}>
            <Icon />
            <span className="nav-lab">{label}</span>
          </button>
        ))}
      </nav>
    </div>
  );
}
