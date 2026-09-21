import { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import Svg, { Circle, Line, Path, Rect, Text as SvgText } from 'react-native-svg';
import { Button, TabRow } from '../components/chrome';
import { colors, fonts } from '../theme';

type Side = 'kicking' | 'planting';

// Trivela is filmed from the OPPOSITE side to laces/finesse (see project design notes) —
// the wrap-around swing only shows up as visible in-frame motion from the
// planting-foot side. This toggle exists so that exception is never silently
// flattened into one generic "stand here" diagram.
const SIDE_LABEL: Record<Side, string> = { kicking: 'kicking-foot', planting: 'planting-foot' };

// react-native-svg's <Text> takes fontSize/fill/letterSpacing as direct
// props (its TS types don't expose a `style` prop), and it doesn't support
// CSS textTransform — so labels are upper-cased inline here instead of via
// stylesheet, unlike the web CSS (fg-lbl / fg-lbl-accent in FilmGuide.css).
function Lbl({
  x, y, textAnchor = 'middle', accent, opacity, children,
}: {
  x: number; y: number; textAnchor?: 'start' | 'middle' | 'end'; accent?: boolean; opacity?: number; children: string | string[];
}) {
  const text = Array.isArray(children) ? children.join('') : children;
  return (
    <SvgText
      x={x}
      y={y}
      textAnchor={textAnchor}
      opacity={opacity}
      fontSize={8.5}
      letterSpacing={0.4}
      fill={accent ? colors.paint : colors.muted}
      fontWeight={accent ? '700' : undefined}
    >
      {text.toUpperCase()}
    </SvgText>
  );
}

// Ported from frontend/src/screens/FilmGuide.tsx. Same viewBox/geometry
// and side-toggle math as the web version — every svg/line/path/circle/
// text tag is a mechanical rename to react-native-svg equivalents.
export default function FilmGuide({ onBack, onContinue }: { onBack: () => void; onContinue?: () => void }) {
  const [side, setSide] = useState<Side>('kicking');
  const sign = side === 'kicking' ? 1 : -1;
  const camX = 160 + sign * 95;

  return (
    <>
      <View style={styles.hd}>
        <Pressable onPress={onBack}>
          <Text style={styles.back}>‹ Back to Assess</Text>
        </Pressable>
        <Text style={styles.eyebrow}>Camera setup</Text>
        <Text style={styles.title}>How to film your shot</Text>
      </View>
      <ScrollView contentContainerStyle={styles.pad} showsVerticalScrollIndicator={false}>
        <TabRow
          options={['kicking', 'planting']}
          labels={['Laces / Finesse', 'Trivela']}
          active={side === 'kicking' ? 0 : 1}
          onChange={i => setSide(i === 0 ? 'kicking' : 'planting')}
        />

        <Text style={styles.sectLabel}>Camera position (bird's-eye view)</Text>
        <View style={styles.card}>
          <Svg viewBox="0 0 320 210" style={styles.svg}>
            <Line x1={160} y1={185} x2={160} y2={28} stroke={colors.line} strokeWidth={2} strokeDasharray="4 4" />
            <Path d="M154,36 L160,24 L166,36 Z" fill={colors.muted} />
            <Lbl x={160} y={16}>shooting direction</Lbl>

            <Circle cx={160} cy={175} r={9} fill={colors.chalk} />
            <Lbl x={160} y={197}>you</Lbl>

            <Circle cx={160} cy={110} r={6} fill={colors.paint} />
            <Lbl x={160 - sign * 22} y={114}>ball</Lbl>

            <Line x1={170} y1={110} x2={camX - sign * 14} y2={110} stroke={colors.line} strokeWidth={1.5} strokeDasharray="3 3" />
            <Lbl x={(160 + camX) / 2} y={102}>~3–4m</Lbl>

            <Path d={`M160,100 L${160 + sign * 10},100 L${160 + sign * 10},110`} fill="none" stroke={colors.muted} strokeWidth={1.5} />
            <Lbl x={160 + sign * 16} y={96} textAnchor={sign > 0 ? 'start' : 'end'} accent>90°</Lbl>

            <Rect x={camX - 9} y={96} width={18} height={28} rx={4} fill={colors.turf3} stroke={colors.chalk} strokeWidth={1.5} />
            <Circle cx={camX} cy={110} r={3.2} fill={colors.paint} />
            <Lbl x={camX} y={140}>camera</Lbl>
            <Lbl x={camX} y={152} accent>{SIDE_LABEL[side]} side</Lbl>
          </Svg>
          <Text style={styles.caption}>
            {side === 'kicking'
              ? 'Laces and finesse: camera side-on, 90° to your shot, on your kicking-foot side.'
              : 'Trivela: camera on your planting-foot side — the opposite of laces and finesse. The wrap-around swing only reads clearly from here.'}
          </Text>
          <View style={styles.tip}>
            <Text style={styles.tipText}>
              <Text style={styles.tipStrong}>Line up to where the ball is actually going</Text> — not your stance or run-up. Same rule whether the shot's straight ahead or angled across goal.
            </Text>
          </View>
        </View>

        <View style={styles.card}>
          <Text style={styles.subhead}>Shot angled across goal — same rule</Text>
          <Svg viewBox="0 0 320 280" style={styles.svg}>
            <Line x1={100} y1={160} x2={100} y2={20} stroke={colors.muted} strokeWidth={1.5} strokeDasharray="3 4" opacity={0.35} />
            <Lbl x={100} y={14} opacity={0.55}>straight ahead (not this)</Lbl>

            <Path d="M200,80 L200,25 L260,25 L260,80" fill="none" stroke={colors.chalk} strokeWidth={3} strokeLinecap="round" strokeLinejoin="round" />
            <Lbl x={230} y={18}>goal</Lbl>

            <Line x1={100} y1={160} x2={230} y2={50} stroke={colors.paint} strokeWidth={2} />
            <Path d="M230,50 L225.6,60.3 L219.1,52.6 Z" fill={colors.paint} />
            <Lbl x={156} y={94} accent>shot line</Lbl>

            <Path d="M112.2,149.7 A16,16 0 0,1 110.3,172.2" fill="none" stroke={colors.muted} strokeWidth={1.5} />
            <Lbl x={128} y={162} accent>90°</Lbl>

            <Line x1={109} y1={170.7} x2={152.4} y2={221.8} stroke={colors.line} strokeWidth={1.5} strokeDasharray="3 3" />
            <Lbl x={137} y={191}>~3–4m</Lbl>

            <Circle cx={100} cy={160} r={6} fill={colors.paint} />
            <Lbl x={76} y={164}>ball</Lbl>

            <Rect x={152.4} y={218.5} width={18} height={28} rx={4} fill={colors.turf3} stroke={colors.chalk} strokeWidth={1.5} />
            <Circle cx={161.4} cy={232.5} r={3.2} fill={colors.paint} />
            <Lbl x={161} y={262}>camera</Lbl>
          </Svg>
          <Text style={styles.caption}>
            The ball isn't lined up straight in front of the goal — the shot line runs diagonally. The camera still goes 90° to that diagonal, on the kicking-foot side, not to an assumed "straight ahead". (Mirror it for trivela, same as the diagram above.)
          </Text>
        </View>

        <Text style={styles.sectLabel}>Steps</Text>
        <View style={styles.steps}>
          {[
            'Place the ball near the centre of frame, not off to one side — it needs room to travel after you strike it.',
            `Stand the phone side-on, 90° to your shooting line, on your ${SIDE_LABEL[side]} side.`,
            "You don't need to be in frame for the whole clip — just be fully in shot for the 8–10 frames before you strike.",
            'Film in slow-mo — 240fps if your phone supports it.',
          ].map((text, i) => (
            <View key={i} style={styles.step}>
              <View style={styles.stepNum}><Text style={styles.stepNumText}>{i + 1}</Text></View>
              <Text style={styles.stepText}>{text}</Text>
            </View>
          ))}
        </View>

        <Text style={styles.sectLabel}>Framing guide</Text>
        <View style={styles.frames}>
          <View style={styles.frame}>
            <Svg viewBox="0 0 100 170" style={styles.frameSvg}>
              <Rect x={4} y={4} width={92} height={162} rx={10} fill="none" stroke={colors.line} strokeWidth={2} />
              <Line x1={10} y1={140} x2={90} y2={140} stroke={colors.line2} strokeWidth={1.5} />
              <Line x1={18} y1={140} x2={40} y2={140} stroke={colors.muted} strokeWidth={1.5} strokeDasharray="2 3" />
              <Line x1={60} y1={140} x2={82} y2={140} stroke={colors.muted} strokeWidth={1.5} strokeDasharray="2 3" />
              <Path d="M18,140 L23,136 L23,144 Z" fill={colors.muted} />
              <Path d="M82,140 L77,136 L77,144 Z" fill={colors.muted} />
              <Circle cx={50} cy={140} r={8} fill={colors.paint} />
            </Svg>
            <Text style={styles.frameCap}><Text style={styles.frameCapStrong}>Ball</Text> centred, with space either side to travel after contact.</Text>
          </View>
          <View style={styles.frame}>
            <Svg viewBox="0 0 100 170" style={styles.frameSvg}>
              <Rect x={4} y={4} width={92} height={162} rx={10} fill="none" stroke={colors.line} strokeWidth={2} />
              <Line x1={10} y1={150} x2={90} y2={150} stroke={colors.line2} strokeWidth={1.5} />
              <Circle cx={45} cy={25} r={9} fill={colors.chalk} />
              <Path d="M45,34 L51,80 L39,80 Z" fill={colors.chalk} />
              <Path d="M42,45 L20,55" stroke={colors.chalk} strokeWidth={4} strokeLinecap="round" />
              <Path d="M48,45 L64,34" stroke={colors.chalk} strokeWidth={4} strokeLinecap="round" />
              <Path d="M43,80 L35,150" stroke={colors.chalk} strokeWidth={6} strokeLinecap="round" />
              <Path d="M48,80 L70,100 L85,90" fill="none" stroke={colors.chalk} strokeWidth={6} strokeLinecap="round" strokeLinejoin="round" />
              <Circle cx={88} cy={88} r={6} fill={colors.paint} />
            </Svg>
            <Text style={styles.frameCap}><Text style={styles.frameCapStrong}>You</Text>, fully in frame for the last 8–10 frames before contact.</Text>
          </View>
        </View>

        {onContinue && (
          <View style={{ marginTop: 20 }}>
            <Button label="Start filming" onPress={onContinue} />
          </View>
        )}
      </ScrollView>
    </>
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
  back: {
    fontFamily: fonts.displayBold,
    color: colors.muted,
    fontSize: 11,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 10,
  },
  eyebrow: {
    fontFamily: fonts.displayBold,
    textTransform: 'uppercase',
    letterSpacing: 2,
    fontSize: 10,
    color: colors.paint,
  },
  title: { fontFamily: fonts.displayBlack, fontSize: 26, color: colors.chalk, marginTop: 4 },
  pad: { paddingHorizontal: 20, paddingVertical: 18 },
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
    paddingTop: 12,
    marginBottom: 10,
  },
  subhead: { fontFamily: fonts.displayBold, fontSize: 12, color: colors.chalk, marginBottom: 6 },
  svg: { width: '100%', aspectRatio: 320 / 210 },
  caption: { fontFamily: fonts.body, fontSize: 12.5, color: colors.muted, lineHeight: 18, marginTop: 10 },
  tip: {
    marginTop: 10,
    padding: 12,
    borderRadius: 10,
    backgroundColor: 'rgba(232,255,79,0.08)',
    borderWidth: 1,
    borderColor: 'rgba(232,255,79,0.3)',
  },
  tipText: { fontFamily: fonts.body, fontSize: 12, color: colors.chalk, lineHeight: 18 },
  tipStrong: { color: colors.paint, fontWeight: '700' },
  steps: { gap: 12 },
  step: { flexDirection: 'row', alignItems: 'flex-start', gap: 10 },
  stepNum: {
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: colors.paint,
    alignItems: 'center',
    justifyContent: 'center',
  },
  stepNumText: { fontFamily: fonts.displayBold, fontWeight: '800', fontSize: 12, color: colors.paintOnDark },
  stepText: { fontFamily: fonts.body, fontSize: 12.5, color: colors.chalk, lineHeight: 18, paddingTop: 2, flex: 1 },
  frames: { flexDirection: 'row', gap: 10 },
  frame: { flex: 1, backgroundColor: colors.turf2, borderWidth: 1, borderColor: colors.line, borderRadius: 14, padding: 10 },
  frameSvg: { width: '100%', aspectRatio: 100 / 170 },
  frameCap: { fontFamily: fonts.body, fontSize: 11.5, color: colors.muted, lineHeight: 17, marginTop: 8 },
  frameCapStrong: { color: colors.chalk, fontWeight: '700' },
});
