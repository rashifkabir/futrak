// Ported 1:1 from frontend/src/index.css `:root` custom properties.
// RN has no CSS custom properties, so this is the single source of truth
// both there and here — keep the two in sync by hand if either changes.
export const colors = {
  turf: '#0d2818',
  turf2: '#123821',
  turf3: '#0a1f13',
  chalk: '#f4f6f0',
  paint: '#e8ff4f',
  clay: '#c9683e',
  line: 'rgba(244,246,240,0.12)',
  line2: 'rgba(244,246,240,0.06)',
  muted: '#7d9384',
  muted2: '#5a6f61',
  good: '#8fe388',
  warn: '#e8b84f',
  bg: '#05100a',
  paintOnDark: '#14210a',
} as const;

// font-family names as registered by expo-font once the Archivo/Inter
// weights are loaded in App.tsx (see loadAsync call).
export const fonts = {
  body: 'Inter_400Regular',
  displayBold: 'Archivo_700Bold',
  displayBlack: 'Archivo_900Black',
} as const;

export const shellMaxWidth = 440;
