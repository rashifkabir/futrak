import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { Button, Card, ScreenBody, ScreenHeader } from '../components/chrome';
import CaptureShot from './CaptureShot';
import FilmGuide from './FilmGuide';
import { CONDITIONS, RANKED_SHOT_TYPES, type AssessmentState, type ShotType } from '../lib/data';
import { colors, fonts } from '../theme';

type Step = 'matrix' | 'guide' | 'capture';

const TYPE_COLOR: Record<ShotType, { bg: string; fg: string }> = {
  laces: { bg: 'rgba(90,160,224,0.16)', fg: '#8fbdec' },
  finesse: { bg: 'rgba(143,227,136,0.14)', fg: colors.good },
  trivela: { bg: 'rgba(232,184,79,0.15)', fg: colors.warn },
};

// Ported from frontend/src/screens/Assess.tsx. The main ranked assessment
// matrix: ranked shot types x 2 conditions. Trivela is deliberately
// excluded (reserved for the £2.50 side-competition path, see
// lib/shotTypes.ts) but its cell/scorer stay intact underneath; only this
// display is filtered. Cells show attempts + honest "—" for scores that
// don't exist yet.
export default function Assess({ assessment }: { assessment: AssessmentState }) {
  const [step, setStep] = useState<Step>('matrix');

  if (step === 'guide') {
    return (
      <FilmGuide
        onBack={() => setStep('matrix')}
        onContinue={() => setStep('capture')}
      />
    );
  }
  if (step === 'capture') {
    return <CaptureShot onBack={() => setStep('guide')} shotType="laces" condition="static" />;
  }

  return (
    <>
      <ScreenHeader eyebrow="Assessment" title="Shooting matrix" />
      <ScreenBody>
        <View style={styles.matrix}>
          <View style={styles.row}>
            <View style={styles.corner} />
            {CONDITIONS.map(c => (
              <View key={c.id} style={styles.condHead}>
                <Text style={styles.condName}>{c.name}</Text>
                <Text style={styles.condNote}>{c.measuresPower ? 'technique + power' : 'technique'}</Text>
              </View>
            ))}
          </View>
          {RANKED_SHOT_TYPES.map(st => (
            <View key={st.id} style={styles.row}>
              <View style={[styles.type, { backgroundColor: TYPE_COLOR[st.id].bg }]}>
                <Text style={[styles.typeLabel, { color: TYPE_COLOR[st.id].fg }]}>{st.name}</Text>
              </View>
              {CONDITIONS.map(c => {
                const cell = assessment[`${st.id}:${c.id}`];
                return (
                  <View key={c.id} style={styles.cell}>
                    <Text style={styles.cellScore}>{cell.score ?? '—'}</Text>
                    <Text style={styles.cellAtt}>{cell.attempts}/{cell.baseAttempts} attempts</Text>
                  </View>
                );
              })}
            </View>
          ))}
        </View>

        <Card
          kicker="Next up"
          title="Laces · Static"
          body="Still ball, side-on at ~90°, full body in frame. The scoring isn't calibrated yet — this is where your shots will be measured once it is."
          style={{ marginTop: 16 }}
        >
          <View style={styles.actions}>
            <Button label="Film attempt" onPress={() => setStep('guide')} />
            <Button label="+2 via ad / £1.50" ghost />
          </View>
        </Card>

        <Text style={styles.note}>Static measures technique and power (still ball). Run-up measures technique only — a moving ball makes power unreliable.</Text>
      </ScreenBody>
    </>
  );
}

const styles = StyleSheet.create({
  matrix: { gap: 8 },
  row: { flexDirection: 'row', gap: 8 },
  corner: { width: 74 },
  condHead: { flex: 1, alignItems: 'center', paddingVertical: 8, paddingHorizontal: 4 },
  condName: { fontFamily: fonts.displayBold, fontSize: 12, color: colors.chalk },
  condNote: { fontFamily: fonts.body, fontSize: 9, color: colors.muted, marginTop: 2 },
  type: {
    width: 74,
    borderRadius: 10,
    padding: 10,
    justifyContent: 'center',
  },
  typeLabel: { fontFamily: fonts.displayBold, fontSize: 11, lineHeight: 13 },
  cell: {
    flex: 1,
    backgroundColor: colors.turf2,
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: 10,
    paddingVertical: 12,
    paddingHorizontal: 6,
    alignItems: 'center',
  },
  cellScore: { fontFamily: fonts.displayBlack, fontSize: 22, color: colors.muted2 },
  cellAtt: { fontFamily: fonts.body, fontSize: 9, color: colors.muted, marginTop: 2 },
  actions: { flexDirection: 'row', gap: 8, marginTop: 12 },
  note: { fontFamily: fonts.body, fontSize: 11, color: colors.muted, marginTop: 14, lineHeight: 17 },
});
