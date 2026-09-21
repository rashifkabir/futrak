import { View } from 'react-native';
import Empty from '../components/Empty';
import { Card, ScreenBody, ScreenHeader } from '../components/chrome';

// Ported from frontend/src/screens/Plan.tsx. Adaptive plan (season pass).
// No weakness can be diagnosed until real assessments exist, so the plan
// is honestly empty, not pre-filled with fake drills.
export default function Plan() {
  return (
    <>
      <ScreenHeader eyebrow="Adaptive plan · season pass" title="Your plan" />
      <ScreenBody>
        <Empty
          title="Nothing to work on yet"
          body="Once you've completed an assessment, your plan targets your weakest measured area, sets drills, and re-tests. It appears here after your first shots."
        />

        <View style={{ marginTop: 14 }}>
          <Card
            kicker="What the pass unlocks"
            title="Plan + full breakdown"
            body="The adaptive drill path, frame-by-frame analysis of each strike, and deeper progress analytics. Competing and winning rewards never require the pass."
          />
        </View>
      </ScreenBody>
    </>
  );
}
