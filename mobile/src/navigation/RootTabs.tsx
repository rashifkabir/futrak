import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { useState } from 'react';
import { IconAssess, IconHome, IconPlan, IconProfile, IconRank } from '../components/icons';
import Assess from '../screens/Assess';
import Home from '../screens/Home';
import Plan from '../screens/Plan';
import Profile from '../screens/Profile';
import Rank from '../screens/Rank';
import { freshAssessment, type AssessmentState } from '../lib/data';
import { colors, fonts } from '../theme';

const Tab = createBottomTabNavigator();

// Assessment state lives above the navigator (same as the single
// `useState` in frontend/src/App.tsx) and is threaded into the two
// screens that read it, since React Navigation screens don't take props
// directly from the navigator the way the web shell's tab switch did.
function useSharedAssessment() {
  const [assessment] = useState<AssessmentState>(freshAssessment());
  return assessment;
}

function HomeScreen() {
  return <Home assessment={useSharedAssessment()} />;
}

function AssessScreen() {
  return <Assess assessment={useSharedAssessment()} />;
}

const TAB_LABEL = { fontFamily: fonts.displayBold, fontSize: 9, textTransform: 'uppercase' as const, letterSpacing: 0.4 };

// Ported from frontend/src/App.tsx's 5-tab shell onto React Navigation's
// bottom-tab-navigator (flat tabs, no nested routes — no Expo Router
// needed). Screens render their own header (ScreenHeader in components/
// chrome.tsx), so the navigator's own header is hidden.
export default function RootTabs() {
  return (
    <Tab.Navigator
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.paint,
        tabBarInactiveTintColor: colors.muted2,
        tabBarStyle: {
          backgroundColor: colors.turf3,
          borderTopColor: colors.line,
          borderTopWidth: 1,
        },
        tabBarLabelStyle: TAB_LABEL,
      }}
    >
      <Tab.Screen
        name="Home"
        component={HomeScreen}
        options={{ tabBarIcon: ({ color }) => <IconHome color={color} /> }}
      />
      <Tab.Screen
        name="Assess"
        component={AssessScreen}
        options={{ tabBarIcon: ({ color }) => <IconAssess color={color} /> }}
      />
      <Tab.Screen
        name="Rank"
        component={Rank}
        options={{ tabBarIcon: ({ color }) => <IconRank color={color} /> }}
      />
      <Tab.Screen
        name="Plan"
        component={Plan}
        options={{ tabBarIcon: ({ color }) => <IconPlan color={color} /> }}
      />
      <Tab.Screen
        name="Profile"
        component={Profile}
        options={{ tabBarIcon: ({ color }) => <IconProfile color={color} /> }}
      />
    </Tab.Navigator>
  );
}
