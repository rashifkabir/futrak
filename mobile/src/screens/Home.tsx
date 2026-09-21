import { View } from 'react-native';
import ScorePlate from '../components/ScorePlate';
import { Card, ScreenBody, ScreenHeader, SectionLabel } from '../components/chrome';
import type { AssessmentState } from '../lib/data';
import { colors, fonts } from '../theme';

// Ported from frontend/src/screens/Home.tsx. The score plate is empty
// until calibration + attempts exist. No fabricated rating, no fake
// "this week" data.
export default function Home({ assessment }: { assessment: AssessmentState }) {
  // shooting rating would aggregate calibrated cells — none exist yet, so null.
  const anyScored = Object.values(assessment).some(c => c.score !== null);
  const rating = anyScored ? null : null; // stays null: no calibrated scorer yet

  return (
    <>
      <ScreenHeader eyebrow="Futra" title="Your shooting" />
      <ScreenBody>
        <ScorePlate
          value={rating}
          label="Shooting rating"
          sub={rating === null ? 'take your first assessment' : undefined}
        />

        <SectionLabel>Next step</SectionLabel>
        <Card kicker="Get started" title="Film your first shot" body="Static laces to begin. One phone, side-on, slow-mo.">
          <View style={{ marginTop: 12 }} />
        </Card>

        <SectionLabel>This season</SectionLabel>
        <Card kicker="Ranking" title="— no rank yet" body="Complete an assessment to enter the ladder." />
      </ScreenBody>
    </>
  );
}
