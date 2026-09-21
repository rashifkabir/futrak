import type { ReactNode } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { colors, fonts } from '../theme';

// Shared screen chrome, ported from the global classNames every screen in
// frontend/src/ uses (screen-hd/screen-pad/sect-label/card/btn/tabs in
// index.css + Shell.css) — kept as one file since RN has no global
// stylesheet equivalent to reuse a className across components.

export function ScreenHeader({ eyebrow, title }: { eyebrow: string; title: string }) {
  return (
    <View style={styles.hd}>
      <Text style={styles.eyebrow}>{eyebrow}</Text>
      <Text style={styles.title}>{title}</Text>
    </View>
  );
}

export function ScreenBody({ children }: { children: ReactNode }) {
  return (
    <ScrollView
      contentContainerStyle={styles.pad}
      showsVerticalScrollIndicator={false}
    >
      {children}
    </ScrollView>
  );
}

export function SectionLabel({ children }: { children: ReactNode }) {
  return <Text style={styles.sectLabel}>{children}</Text>;
}

export function Card({
  kicker,
  title,
  body,
  style,
  children,
}: {
  kicker: string;
  title: string;
  body: string;
  style?: object;
  children?: ReactNode;
}) {
  return (
    <View style={[styles.card, style]}>
      <Text style={styles.cardK}>{kicker}</Text>
      <Text style={styles.cardT}>{title}</Text>
      <Text style={styles.cardD}>{body}</Text>
      {children}
    </View>
  );
}

export function Button({
  label,
  onPress,
  ghost = false,
}: {
  label: string;
  onPress?: () => void;
  ghost?: boolean;
}) {
  return (
    <Pressable
      onPress={onPress}
      style={[styles.btn, ghost && styles.btnGhost]}
      disabled={!onPress}
    >
      <Text style={[styles.btnLabel, ghost && styles.btnGhostLabel]}>{label}</Text>
    </Pressable>
  );
}

export function TabRow<T extends string>({
  options,
  labels,
  active,
  onChange,
}: {
  options: T[];
  labels?: string[];
  active: number;
  onChange: (i: number) => void;
}) {
  return (
    <View style={styles.tabs}>
      {options.map((opt, i) => (
        <Pressable
          key={opt}
          onPress={() => onChange(i)}
          style={[styles.tab, i === active && styles.tabOn]}
        >
          <Text style={[styles.tabLabel, i === active && styles.tabLabelOn]}>
            {labels ? labels[i] : opt}
          </Text>
        </Pressable>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  hd: {
    paddingTop: 22,
    paddingHorizontal: 20,
    paddingBottom: 18,
    borderBottomWidth: 1,
    borderBottomColor: colors.line2,
    backgroundColor: colors.turf3,
  },
  eyebrow: {
    fontFamily: fonts.displayBold,
    textTransform: 'uppercase',
    letterSpacing: 2,
    fontSize: 10,
    color: colors.paint,
  },
  title: {
    fontFamily: fonts.displayBlack,
    fontSize: 26,
    color: colors.chalk,
    marginTop: 4,
  },
  pad: {
    paddingHorizontal: 20,
    paddingVertical: 18,
  },
  sectLabel: {
    fontFamily: fonts.displayBold,
    textTransform: 'uppercase',
    letterSpacing: 1,
    fontSize: 11,
    color: colors.muted,
    marginTop: 22,
    marginBottom: 12,
  },
  card: {
    backgroundColor: colors.turf2,
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: 14,
    padding: 15,
    marginBottom: 10,
  },
  cardK: {
    fontFamily: fonts.displayBold,
    textTransform: 'uppercase',
    letterSpacing: 0.6,
    fontSize: 10,
    color: colors.muted,
  },
  cardT: {
    fontFamily: fonts.displayBold,
    fontSize: 16,
    color: colors.chalk,
    marginTop: 3,
  },
  cardD: {
    fontFamily: fonts.body,
    fontSize: 12.5,
    color: colors.muted,
    marginTop: 4,
    lineHeight: 18,
  },
  btn: {
    alignSelf: 'flex-start',
    backgroundColor: colors.paint,
    paddingVertical: 11,
    paddingHorizontal: 18,
    borderRadius: 22,
  },
  btnGhost: {
    backgroundColor: 'transparent',
    borderWidth: 1.5,
    borderColor: colors.line,
    paddingVertical: 9,
    paddingHorizontal: 16,
  },
  btnLabel: {
    fontFamily: fonts.displayBold,
    fontSize: 13,
    textTransform: 'uppercase',
    letterSpacing: 0.4,
    color: colors.paintOnDark,
  },
  btnGhostLabel: {
    color: colors.chalk,
  },
  tabs: {
    flexDirection: 'row',
    gap: 7,
    marginBottom: 8,
  },
  tab: {
    flex: 1,
    paddingVertical: 9,
    paddingHorizontal: 4,
    borderRadius: 10,
    backgroundColor: colors.turf2,
    borderWidth: 1,
    borderColor: colors.line,
    alignItems: 'center',
  },
  tabOn: {
    backgroundColor: colors.paint,
    borderColor: colors.paint,
  },
  tabLabel: {
    fontFamily: fonts.displayBold,
    fontSize: 11,
    textTransform: 'uppercase',
    letterSpacing: 0.3,
    color: colors.muted,
  },
  tabLabelOn: {
    color: colors.paintOnDark,
  },
});
