import { StyleSheet, Text, View } from 'react-native';
import { colors, fonts } from '../theme';

interface Props {
  value: number | null;
  label: string;
  sub?: string;
  size?: 'lg' | 'md' | 'sm';
}

const NUM_SIZE: Record<NonNullable<Props['size']>, number> = { lg: 64, md: 44, sm: 30 };
const LABEL_SIZE: Record<NonNullable<Props['size']>, number> = { lg: 12, md: 11, sm: 11 };

// Ported from frontend/src/components/ScorePlate.tsx. The signature
// element. When value is null the plate shows an honest empty state
// ("—" + reason) instead of a fabricated score.
export default function ScorePlate({ value, label, sub, size = 'lg' }: Props) {
  const empty = value === null;
  return (
    <View style={styles.plate}>
      <Text
        style={[
          styles.num,
          { fontSize: NUM_SIZE[size] },
          empty && styles.numEmpty,
        ]}
      >
        {empty ? '—' : value}
      </Text>
      <View>
        <Text style={[styles.label, { fontSize: LABEL_SIZE[size] }]}>{label}</Text>
        {sub && <Text style={styles.sub}>{sub}</Text>}
        {empty && !sub && <Text style={styles.sub}>not yet measured</Text>}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  plate: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
    backgroundColor: colors.turf2,
    borderRadius: 16,
    paddingVertical: 18,
    paddingHorizontal: 20,
    borderWidth: 1,
    borderColor: colors.line,
  },
  num: {
    fontFamily: fonts.displayBlack,
    color: colors.paint,
    letterSpacing: -1,
  },
  numEmpty: {
    color: colors.muted2,
  },
  label: {
    fontFamily: fonts.displayBold,
    textTransform: 'uppercase',
    letterSpacing: 1,
    color: colors.muted,
  },
  sub: {
    fontFamily: fonts.body,
    fontSize: 12,
    color: colors.muted,
    marginTop: 3,
  },
});
