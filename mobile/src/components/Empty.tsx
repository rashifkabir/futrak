import { StyleSheet, Text, View } from 'react-native';
import { colors, fonts } from '../theme';

// Ported from frontend/src/components/Empty.tsx. A reusable honest empty
// state. Used everywhere a feature isn't finalised — per the build rule,
// unfinalised things are genuinely empty, and say why.
export default function Empty({ title, body }: { title: string; body: string }) {
  return (
    <View style={styles.empty}>
      <Text style={styles.mark} accessibilityElementsHidden>—</Text>
      <Text style={styles.title}>{title}</Text>
      <Text style={styles.body}>{body}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  empty: {
    borderWidth: 1,
    borderStyle: 'dashed',
    borderColor: colors.line,
    borderRadius: 14,
    paddingVertical: 26,
    paddingHorizontal: 20,
    alignItems: 'center',
  },
  mark: {
    fontFamily: fonts.displayBlack,
    fontSize: 32,
    color: colors.muted2,
    lineHeight: 32,
  },
  title: {
    fontFamily: fonts.displayBold,
    color: colors.chalk,
    fontSize: 15,
    marginTop: 8,
    textAlign: 'center',
  },
  body: {
    fontFamily: fonts.body,
    fontSize: 12.5,
    color: colors.muted,
    marginTop: 6,
    lineHeight: 18,
    maxWidth: 240,
    textAlign: 'center',
  },
});
