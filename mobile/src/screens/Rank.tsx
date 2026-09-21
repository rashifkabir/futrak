import { useState } from 'react';
import { View } from 'react-native';
import Empty from '../components/Empty';
import { Card, ScreenBody, ScreenHeader, TabRow } from '../components/chrome';
import { LOCATIONS, RANKED_SHOT_TYPES } from '../lib/data';

// Ported from frontend/src/screens/Rank.tsx. Leaderboards: Location x
// ranked Shot type. Genuinely empty — no fake players, no invented scores.
// Ladder populates once real assessments exist. Trivela is deliberately
// excluded (reserved for the £2.50 side-competition path, see
// lib/shotTypes.ts), same as the Assess matrix.
export default function Rank() {
  const [loc, setLoc] = useState(0);
  const [st, setSt] = useState(0);

  return (
    <>
      <ScreenHeader eyebrow="Season · leaderboards" title="Rank" />
      <ScreenBody>
        <TabRow options={LOCATIONS as unknown as string[]} active={loc} onChange={setLoc} />
        <TabRow
          options={RANKED_SHOT_TYPES.map(s => s.id)}
          labels={RANKED_SHOT_TYPES.map(s => s.name.split(' ')[0])}
          active={st}
          onChange={setSt}
        />

        <View style={{ marginTop: 14 }}>
          <Empty
            title="No rankings yet"
            body={`The ${LOCATIONS[loc]} · ${RANKED_SHOT_TYPES[st].name} ladder fills once players complete verified assessments. Yours could be the first.`}
          />
        </View>

        <View style={{ marginTop: 14 }}>
          <Card
            kicker="Monthly reward · top of the ladder"
            title="Session or remote analysis"
            body="London winners: a UEFA-coach group session. Outside London: bespoke remote analysis. Verification is free and required before month-end. Earned by skill — never bought."
          />
        </View>
      </ScreenBody>
    </>
  );
}
