---
title: "Accessibility in React: the ARIA patterns that actually matter."
description: "The ARIA attributes and accessibility patterns that have the most impact on screen reader users, with React implementation examples."
pubDate: 2025-09-15
tags: ["DevOps"]
draft: false
---

Accessibility in React is often treated as an audit checkbox rather than a set of concrete implementation patterns. The gap between "passing a Lighthouse accessibility score" and "usable by a screen reader user" is large. These are the ARIA patterns that make an actual difference.

## Semantic HTML first

Before any ARIA, use semantic HTML. ARIA fills gaps that HTML cannot express. Using ARIA to patch non-semantic HTML is always harder than using the right element in the first place.

```jsx
// Wrong: div buttons have no implicit role, no keyboard interaction
<div onClick={handleSubmit} className="btn">Submit</div>

// Right: button has implicit role="button", responds to Enter/Space, focusable
<button onClick={handleSubmit}>Submit</button>
```

Screen readers announce the button role automatically. Keyboard users can Tab to it and activate it. None of this requires ARIA.

Use `<nav>`, `<main>`, `<header>`, `<footer>`, `<aside>` for landmark regions. Screen reader users navigate by landmarks. A page without landmarks requires linear reading from top to bottom.

## aria-label and aria-labelledby

When the visual context makes an element's purpose clear but that context is not expressed in the DOM, add an explicit label.

```jsx
// Icon-only button: sighted users understand the X means close,
// screen reader users hear "button" with no context
<button onClick={onClose}>
  <XIcon />
</button>

// With aria-label, screen reader announces "Close dialog, button"
<button onClick={onClose} aria-label="Close dialog">
  <XIcon aria-hidden="true" />
</button>
```

`aria-hidden="true"` on the icon prevents it from being announced (it has no useful text content). The `aria-label` provides the meaningful name.

`aria-labelledby` references another element's ID as the label:

```jsx
<h2 id="billing-section">Billing Information</h2>
<form aria-labelledby="billing-section">
  ...
</form>
```

The form is now labeled by the visible heading. Screen readers announce "Billing Information, form" when the user enters the form region.

## Live regions for dynamic content

When content updates without a page reload, screen readers do not automatically announce the change. Live regions tell screen readers to announce content as it appears.

```jsx
function Toast({ message, type }) {
  return (
    <div
      role="status"      // polite: waits for current announcement to finish
      aria-live="polite"
      aria-atomic="true" // announce the entire region, not just the changed part
    >
      {message}
    </div>
  );
}

// For urgent alerts use role="alert" (same as aria-live="assertive")
function ErrorBanner({ error }) {
  return (
    <div role="alert">
      {error}
    </div>
  );
}
```

`role="status"` / `aria-live="polite"` announces after the current interaction completes. `role="alert"` / `aria-live="assertive"` interrupts immediately. Use polite for status messages, assertive for errors.

The live region must be present in the DOM before content is inserted into it. Mounting the region and adding content simultaneously is unreliable. Mount the empty container, then populate it.

## Focus management in modals

When a modal opens, focus must move into it. When it closes, focus must return to the trigger element. Without this, keyboard users lose their place on the page.

```jsx
import { useEffect, useRef } from 'react';

function Modal({ isOpen, onClose, children }) {
  const modalRef = useRef(null);
  const previousFocusRef = useRef(null);

  useEffect(() => {
    if (isOpen) {
      previousFocusRef.current = document.activeElement;
      // Focus the modal container or the first focusable element inside
      modalRef.current?.focus();
    } else {
      // Return focus to where it was before the modal opened
      previousFocusRef.current?.focus();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
      tabIndex={-1}
      ref={modalRef}
    >
      <h2 id="modal-title">Confirm Delete</h2>
      {children}
      <button onClick={onClose}>Cancel</button>
    </div>
  );
}
```

`tabIndex={-1}` makes the container programmatically focusable without adding it to the Tab order. `role="dialog"` and `aria-modal="true"` tell screen readers the modal is active.

## Form errors

Associating error messages with their fields is critical for screen reader users who cannot scan visually.

```jsx
function FormField({ id, label, error, ...props }) {
  const errorId = error ? `${id}-error` : undefined;

  return (
    <div>
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        aria-describedby={errorId}
        aria-invalid={error ? 'true' : undefined}
        {...props}
      />
      {error && (
        <span id={errorId} role="alert">
          {error}
        </span>
      )}
    </div>
  );
}
```

`aria-describedby` links the input to its error message by ID. `aria-invalid="true"` signals that the field is in an error state. Screen readers announce both when the user focuses the field.

## Testing

Install `eslint-plugin-jsx-a11y` to catch common accessibility errors at write time. Run `axe-core` in tests to catch issues automatically:

```javascript
import { axe, toHaveNoViolations } from 'jest-axe';
expect.extend(toHaveNoViolations);

test('modal has no accessibility violations', async () => {
  const { container } = render(<Modal isOpen={true} onClose={() => {}} />);
  const results = await axe(container);
  expect(results).toHaveNoViolations();
});
```

Automated testing catches about 30% of accessibility issues. For the rest, use a screen reader (NVDA on Windows, VoiceOver on macOS) and keyboard navigation. Test by unplugging the mouse.
