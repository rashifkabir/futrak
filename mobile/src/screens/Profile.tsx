import { StyleSheet, Text, View } from 'react-native';
import { Card, ScreenBody, ScreenHeader, SectionLabel } from '../components/chrome';
import { ATTRIBUTES } from '../lib/data';
import { colors, fonts } from '../theme';

// Ported from frontend/src/screens/Profile.tsx. Shooting shown as the
// FIRST attribute (live), others visible but honestly locked as "coming"
// — so shooting reads as v1's attribute, not the only attribute the
// platform will ever have.
export default function Profile() {
  return (
    <>
      <ScreenHeader eyebrow="Profile" title="Player card" />
      <ScreenBody>
        <View style={styles.pcard}>
          <Text style={styles.pcardName}>Set up your profile</Text>
          <Text style={styles.pcardMeta}>Position · foot · age band · location — added when you register.</Text>
        </View>

        <SectionLabel>Attributes</SectionLabel>
        {ATTRIBUTES.map(a => (
          <View key={a.id} style={[styles.attr, a.status === 'coming' && styles.attrComing]}>
            <Text style={styles.attrName}>{a.name}</Text>
            {a.status === 'live'
              ? <Text style={styles.attrVal}>—</Text>
              : <Text style={styles.attrLock}>Coming</Text>}
          </View>
        ))}
        <Text style={styles.attrNote}>Shooting is the first attribute at launch. Finishing, pace and dribbling arrive in later releases.</Text>

        <SectionLabel>v1 products</SectionLabel>
        <Card
          kicker="Season pass"
          title="Adaptive plan + full breakdown"
          body="Deep analysis, extra attempts, status. Never gates competing or rewards."
        />
        <Card
          kicker="One-off"
          title="Verified Performance Portfolio"
          body="An official record of your measured scores and best clips. Framework calibrated with a UEFA-licensed coach."
        />
      </ScreenBody>
    </>
  );
}

const styles = StyleSheet.create({
  pcard: {
    backgroundColor: colors.turf2,
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: 16,
    padding: 18,
  },
  pcardName: {
    fontFamily: fonts.displayBold,
    fontWeight: '800',
    fontSize: 18,
    color: colors.chalk,
  },
  pcardMeta: {
    fontFamily: fonts.body,
    fontSize: 12,
    color: colors.muted,
    marginTop: 4,
  },
  attr: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: colors.turf2,
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: 12,
    paddingVertical: 13,
    paddingHorizontal: 15,
    marginBottom: 8,
  },
  attrComing: {
    opacity: 0.55,
  },
  attrName: {
    fontFamily: fonts.displayBold,
    fontSize: 14,
    color: colors.chalk,
  },
  attrVal: {
    fontFamily: fonts.displayBlack,
    fontSize: 22,
    color: colors.muted2,
  },
  attrLock: {
    fontFamily: fonts.displayBold,
    fontSize: 10,
    textTransform: 'uppercase',
    letterSpacing: 0.6,
    color: colors.muted,
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: 20,
    paddingVertical: 4,
    paddingHorizontal: 10,
  },
  attrNote: {
    fontFamily: fonts.body,
    fontSize: 11,
    color: colors.muted,
    marginTop: 10,
    lineHeight: 17,
  },
});
