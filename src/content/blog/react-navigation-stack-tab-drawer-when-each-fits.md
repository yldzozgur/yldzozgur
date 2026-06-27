---
title: "React Navigation: Stack, Tab, Drawer and when each one fits."
description: "The three core navigators in React Navigation, what each one renders natively, and the patterns that work well for real mobile apps."
pubDate: 2025-02-03
tags: ["React Native", "Mobile", "Navigation"]
draft: false
---

## Navigation as a hierarchy

Mobile navigation is hierarchical. At the top level you usually have a primary structure (bottom tabs, a drawer). Inside each tab you often have a stack for drilling into details. React Navigation models this hierarchy explicitly -- navigators can be nested, and each level manages its own navigation state.

## Stack Navigator

The Stack Navigator renders a stack of screens. Navigating to a new screen pushes it onto the stack; going back pops it. On iOS this produces the standard right-to-left slide transition. On Android it produces an upward slide.

```javascript
import { createNativeStackNavigator } from '@react-navigation/native-stack';

const Stack = createNativeStackNavigator();

function ProductsStack() {
  return (
    <Stack.Navigator>
      <Stack.Screen name="ProductList" component={ProductListScreen} />
      <Stack.Screen name="ProductDetail" component={ProductDetailScreen} />
      <Stack.Screen name="Checkout" component={CheckoutScreen} />
    </Stack.Navigator>
  );
}
```

Passing data between screens uses the `params` object:

```javascript
// Navigate and pass data
navigation.navigate('ProductDetail', { productId: 42 });

// Receive in the destination screen
function ProductDetailScreen({ route }) {
  const { productId } = route.params;
  // ...
}
```

The Stack Navigator is the default choice for any flow that has depth: product browsing, settings, forms, and any screen that leads to another screen.

## Tab Navigator

The Bottom Tab Navigator renders a persistent tab bar at the bottom of the screen. Each tab is its own navigation tree that maintains state independently.

```javascript
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';

const Tab = createBottomTabNavigator();

function AppTabs() {
  return (
    <Tab.Navigator>
      <Tab.Screen name="Home" component={HomeStack} />
      <Tab.Screen name="Search" component={SearchStack} />
      <Tab.Screen name="Profile" component={ProfileStack} />
    </Tab.Navigator>
  );
}
```

Notice that each tab's `component` is itself a Stack Navigator. This is the standard pattern: tabs at the top level, stacks inside each tab. When the user navigates to a product from the Search tab, the stack exists within that tab. Switching to the Home tab shows the home stack, and switching back to Search returns to wherever they were in the search flow.

The Tab Navigator works best for apps with three to five primary destinations that are equally important and accessed frequently.

## Drawer Navigator

The Drawer Navigator puts navigation links in a panel that slides in from the side. It's less common in modern apps but still the right choice for certain contexts.

```javascript
import { createDrawerNavigator } from '@react-navigation/drawer';

const Drawer = createDrawerNavigator();

function AppDrawer() {
  return (
    <Drawer.Navigator>
      <Drawer.Screen name="Dashboard" component={DashboardScreen} />
      <Drawer.Screen name="Reports" component={ReportsScreen} />
      <Drawer.Screen name="Settings" component={SettingsScreen} />
    </Drawer.Navigator>
  );
}
```

The drawer is appropriate for apps with many navigation destinations that don't all need to be visible at once -- admin dashboards, tools with many sections, or apps where a persistent tab bar would be cluttered.

## Nesting navigators

The real power is in combining them. A typical app structure:

```javascript
function App() {
  return (
    <NavigationContainer>
      <Tab.Navigator>
        <Tab.Screen name="HomeTab" component={HomeStackNavigator} />
        <Tab.Screen name="SearchTab" component={SearchStackNavigator} />
        <Tab.Screen name="ProfileTab" component={ProfileStackNavigator} />
      </Tab.Navigator>
    </NavigationContainer>
  );
}

function HomeStackNavigator() {
  return (
    <Stack.Navigator>
      <Stack.Screen name="Feed" component={FeedScreen} />
      <Stack.Screen name="Post" component={PostScreen} />
    </Stack.Navigator>
  );
}
```

Each tab gets its own stack, and the tab bar persists across all stack screens within that tab.

## When to use which

- **Stack**: whenever there's a parent-child relationship between screens (list to detail, form to confirmation)
- **Tab**: three to five primary destinations, all equally important, used frequently
- **Drawer**: many destinations, or destinations that are secondary to the main content

Most apps use all three: a drawer or tabs at the top level, stacks inside. The choice depends on the information architecture, not the technology.
