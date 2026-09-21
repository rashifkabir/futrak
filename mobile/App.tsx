import { Archivo_700Bold, Archivo_900Black } from '@expo-google-fonts/archivo';
import { Inter_400Regular } from '@expo-google-fonts/inter';
import { NavigationContainer } from '@react-navigation/native';
import { useFonts } from 'expo-font';
import * as SplashScreen from 'expo-splash-screen';
import { useEffect } from 'react';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import RootTabs from './src/navigation/RootTabs';
import { colors } from './src/theme';

SplashScreen.preventAutoHideAsync();

const navTheme = {
  dark: true,
  colors: {
    primary: colors.paint,
    background: colors.turf,
    card: colors.turf3,
    text: colors.chalk,
    border: colors.line,
    notification: colors.paint,
  },
  fonts: {
    regular: { fontFamily: 'Inter_400Regular', fontWeight: '400' as const },
    medium: { fontFamily: 'Archivo_700Bold', fontWeight: '700' as const },
    bold: { fontFamily: 'Archivo_700Bold', fontWeight: '700' as const },
    heavy: { fontFamily: 'Archivo_900Black', fontWeight: '900' as const },
  },
};

export default function App() {
  const [fontsLoaded] = useFonts({ Archivo_700Bold, Archivo_900Black, Inter_400Regular });

  useEffect(() => {
    if (fontsLoaded) SplashScreen.hideAsync();
  }, [fontsLoaded]);

  if (!fontsLoaded) return null;

  return (
    <SafeAreaProvider>
      <StatusBar style="light" />
      <NavigationContainer theme={navTheme}>
        <RootTabs />
      </NavigationContainer>
    </SafeAreaProvider>
  );
}
