// The 4 Stage 1/2 demo fixtures — kept alongside real seeded/user-added
// pitches (see lib/pitches.ts) so the crown-state UI (mine/lost/other/
// unclaimed) stays visible and testable. Real pitches have no backend to
// hold crown data yet, so they're always 'unclaimed'; these 4 are the only
// ones with fabricated king/challenger data, which is why they're clearly
// tagged `source: 'demo'` rather than mixed in as if they were real.
//
// lat/lng are real (approximate) coordinates for these actual London parks.

import type { Pitch } from './pitches';

export const MOCK_PITCHES: Pitch[] = [
  {
    id: 'demo:victoria-park',
    name: 'Victoria Park 5-a-side',
    area: 'Hackney',
    lat: 51.5361,
    lng: -0.0388,
    source: 'demo',
    verified: true,
    crownState: 'mine',
    king: { name: 'You', band: 'Very good', power: 71, heldSinceDays: 9, timesDefended: 2 },
    challengers: [
      { rank: 2, name: 'Player 2', band: 'Very good', power: 68 },
      { rank: 3, name: 'Player 3', band: 'Good', power: 60 },
      { rank: 4, name: 'Player 4', band: 'Good', power: 55 },
    ],
  },
  {
    id: 'demo:well-st-common',
    name: 'Well St Common',
    area: 'Hackney',
    lat: 51.549,
    lng: -0.047,
    source: 'demo',
    verified: true,
    crownState: 'lost',
    king: { name: 'Player 5', band: 'Elite', power: 84, heldSinceDays: 3, timesDefended: 1 },
    challengers: [
      { rank: 2, name: 'You', band: 'Very good', power: 71 },
      { rank: 3, name: 'Player 6', band: 'Good', power: 58 },
    ],
  },
  {
    id: 'demo:hackney-marshes-3',
    name: 'Hackney Marshes — Pitch 3',
    area: 'Hackney Marshes',
    lat: 51.5537,
    lng: -0.0339,
    source: 'demo',
    verified: true,
    crownState: 'other',
    king: { name: 'Player 7', band: 'Elite', power: 88, heldSinceDays: 21, timesDefended: 4 },
    challengers: [
      { rank: 2, name: 'Player 8', band: 'Very good', power: 74 },
      { rank: 3, name: 'Player 9', band: 'Good', power: 62 },
    ],
  },
  {
    id: 'demo:london-fields',
    name: 'London Fields',
    area: 'Hackney',
    lat: 51.5405,
    lng: -0.0575,
    source: 'demo',
    verified: true,
    crownState: 'unclaimed',
    king: null,
    challengers: [],
  },
];
