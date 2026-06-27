---
title: "Why utility-first CSS feels wrong for 3 days and right forever after."
description: "The mental shift required to write Tailwind CSS, why HTML with long class strings looks like a mistake at first, and why it stops feeling that way."
pubDate: 2025-01-13
tags: ["Tailwind", "CSS"]
draft: false
---

## The first reaction

When most developers see Tailwind CSS for the first time, the reaction is consistent:

```html
<button class="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded-lg shadow-sm transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2">
  Submit
</button>
```

This looks like inline styles got out of control. It violates the principle of separation of concerns -- HTML for structure, CSS for style. The class string is long enough to require horizontal scrolling. It feels wrong.

That feeling is accurate, but it's responding to the wrong thing. The discomfort is not about bad code. It's about a violated habit.

## What utility-first is solving

The traditional CSS workflow has a specific failure mode: over time, stylesheet files grow, class names multiply, and styles become entangled. You want to change the padding on a card, but the `.card` class is shared across seven components. Changing it breaks three of them.

The solution developers reach for is more specificity, more classes, more nesting. The stylesheet grows more abstract and harder to reason about.

Utility-first inverts this. Instead of naming things and attaching styles to names, you apply the styles directly. There is no `.card` class to accidentally break. There is no stylesheet growing in the background. Every style is visible, at the point of use, inline in the markup.

## The three days

The discomfort has a predictable timeline. On day one, the HTML looks verbose and the classes feel meaningless. On day two, you start recognizing patterns -- `flex items-center gap-4` is always the same horizontal layout, `text-sm text-gray-500` is always metadata text. On day three, you notice you haven't opened a CSS file once.

By day four, the traditional workflow starts feeling slow. You think of a style change, you make it in one place, done. No hunting for the right class name. No wondering whether changing that class will break something else.

## The separation-of-concerns objection

The strongest objection to utility-first CSS is that it mixes concerns: HTML should describe structure, CSS should describe presentation.

This principle was important when HTML and CSS lived in separate files maintained by different people. In a component-based architecture, the "component" is the unit of separation. A button component's structure and its appearance are already coupled -- they are the same thing. Splitting them across files does not reduce coupling; it just spreads it across more locations.

When the component owns its markup and its styles together, changes are local. There is no stylesheet to update, no class naming convention to follow, no cascade to reason about.

## Practical advantages

**No naming problems.** Coming up with meaningful class names is genuinely hard. `.container-wrapper-inner` exists in every codebase. Utilities eliminate the problem entirely.

**No dead CSS.** When you delete a component, you delete all its styles automatically. There is no stylesheet collecting unused rules.

**Constraints by default.** Tailwind's spacing scale, color palette, and font sizes are a design system. Using `p-4` instead of `padding: 17px` keeps the application visually consistent without effort.

**Fast iteration.** Changing a style means changing a class name in JSX. The feedback loop is immediate. No context switching between files.

## The component abstraction layer

Utility classes in one-off HTML are verbose. In a component system, you extract the repetition:

```javascript
function Button({ children, variant = 'primary' }) {
  const base = "font-semibold py-2 px-4 rounded-lg transition-colors duration-150";
  const variants = {
    primary: "bg-blue-600 hover:bg-blue-700 text-white",
    secondary: "bg-gray-100 hover:bg-gray-200 text-gray-900",
  };
  return <button className={`${base} ${variants[variant]}`}>{children}</button>;
}
```

The long string lives in one place. Every `<Button>` in the application shares it. The component is the abstraction, not the class name.

After a week of this, going back to a BEM stylesheet feels like writing assembly.
