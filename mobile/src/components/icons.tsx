import Svg, { Circle, Path } from 'react-native-svg';

// Ported from frontend/src/components/icons.tsx — same paths, mechanical
// tag translation (svg/path/circle -> react-native-svg components).
const stroke = {
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.8,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
};

// react-native-svg doesn't support `currentColor`; callers pass an explicit
// color instead (nav tint) since RN has no CSS `color` inheritance.
type IconProps = { color: string; size?: number };

export const IconHome = ({ color, size = 22 }: IconProps) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" {...stroke} stroke={color}>
    <Path d="M3 11l9-7 9 7" />
    <Path d="M5 10v9h14v-9" />
  </Svg>
);

export const IconAssess = ({ color, size = 22 }: IconProps) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" {...stroke} stroke={color}>
    <Circle cx={12} cy={12} r={8} />
    <Path d="M12 4v4M12 16v4M4 12h4M16 12h4" />
  </Svg>
);

export const IconRank = ({ color, size = 22 }: IconProps) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" {...stroke} stroke={color}>
    <Path d="M6 20V10M12 20V4M18 20v-7" />
  </Svg>
);

export const IconPlan = ({ color, size = 22 }: IconProps) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" {...stroke} stroke={color}>
    <Path d="M5 5h14M5 12h14M5 19h9" />
  </Svg>
);

export const IconProfile = ({ color, size = 22 }: IconProps) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" {...stroke} stroke={color}>
    <Circle cx={12} cy={8} r={4} />
    <Path d="M4 20c0-4 4-6 8-6s8 2 8 6" />
  </Svg>
);
