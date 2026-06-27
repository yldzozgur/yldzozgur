---
title: "Dark mode in Tailwind: class strategy vs media query."
description: "Tailwind supports two dark mode strategies. Here is what each one does, how to implement both, and when to choose one over the other."
pubDate: 2025-01-20
tags: ["Tailwind", "CSS", "Dark Mode"]
draft: false
---

## Two strategies for dark mode

Tailwind has a `dark:` prefix that applies styles only in dark mode. The question is: what triggers dark mode? There are two options, controlled by the `darkMode` setting in `tailwind.config.js`.

**Media query strategy (default):**

```javascript
// tailwind.config.js
module.exports = {
  darkMode: 'media', // or omit entirely, this is the default
};
```

Styles prefixed with `dark:` activate when the user's OS is set to dark mode (`prefers-color-scheme: dark`).

**Class strategy:**

```javascript
module.exports = {
  darkMode: 'class',
};
```

Styles prefixed with `dark:` activate when a parent element (usually `<html>`) has the `dark` class.

## Using the dark: prefix

With either strategy, the syntax in your markup is identical:

```html
<div class="bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100">
  <h1 class="text-2xl font-bold">Hello</h1>
  <p class="text-gray-600 dark:text-gray-400">Some content here.</p>
</div>
```

In light mode: white background, dark text. In dark mode: near-black background, light text. The `dark:` variants are generated for every utility, so you can dark-mode any property.

## The media query strategy

With `darkMode: 'media'`, dark mode is entirely driven by the operating system. You write your styles, and the user's preference controls the toggle. No JavaScript required.

The limitation: you cannot build a manual toggle. If a user wants to override their OS setting and use light mode on a dark-mode OS, you cannot do that with the media strategy. The OS is the only control.

For sites where matching the OS preference is always correct -- documentation, marketing pages -- the media strategy is simpler and needs no JavaScript.

## The class strategy

With `darkMode: 'class'`, Tailwind applies dark styles when `<html>` has the `dark` class (or whichever element you configure as the selector). You manage that class with JavaScript.

A simple implementation that respects OS preference by default but allows toggling:

```javascript
// On page load, check for saved preference
const savedTheme = localStorage.getItem('theme');
const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

if (savedTheme === 'dark' || (!savedTheme && prefersDark)) {
  document.documentElement.classList.add('dark');
}

// Toggle function
function toggleDarkMode() {
  const isDark = document.documentElement.classList.toggle('dark');
  localStorage.setItem('theme', isDark ? 'dark' : 'light');
}
```

In React, this often lives in a context provider:

```javascript
function ThemeProvider({ children }) {
  const [dark, setDark] = useState(() => {
    const saved = localStorage.getItem('theme');
    if (saved) return saved === 'dark';
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  });

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark);
    localStorage.setItem('theme', dark ? 'dark' : 'light');
  }, [dark]);

  return (
    <ThemeContext.Provider value={{ dark, toggle: () => setDark(d => !d) }}>
      {children}
    </ThemeContext.Provider>
  );
}
```

## Avoiding flash of wrong theme

With the class strategy, there is a risk: if you set the `dark` class in a React effect, the page renders in light mode first, then flips to dark. This is a visible flash.

The fix is to run the theme detection in a `<script>` tag before React hydrates, in the `<head>`:

```html
<script>
  (function() {
    const saved = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    if (saved === 'dark' || (!saved && prefersDark)) {
      document.documentElement.classList.add('dark');
    }
  })();
</script>
```

This runs synchronously before any rendering, so the correct theme is applied before the user sees anything.

## Which strategy to choose

Use **media** if:
- You don't need a manual toggle
- The site should always match the OS preference
- You want zero JavaScript for theme handling

Use **class** if:
- You are building a user-controlled theme toggle
- The app has an authenticated user whose preference you store on the server
- You need the same UI to support both themes simultaneously (e.g., a component preview tool)

Most applications with any kind of user preference management should use the class strategy.
