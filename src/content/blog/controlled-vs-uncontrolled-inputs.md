---
title: "Controlled vs uncontrolled inputs: why mixing them causes unreproducible bugs."
description: "The difference between controlled and uncontrolled form inputs in React, why switching between them causes warnings and bugs, and when to use each approach."
pubDate: 2024-12-05
tags: ["React"]
draft: false
---

React inputs come in two modes. Understanding the difference is necessary for writing form logic that behaves predictably.

## Controlled inputs

A controlled input is one where React owns the value. You set the `value` prop, and you update it through `onChange`. The input displays whatever React tells it to display.

```jsx
function ControlledInput() {
  const [name, setName] = useState('');

  return (
    <input
      value={name}
      onChange={(e) => setName(e.target.value)}
    />
  );
}
```

The user types a character. The browser fires `onChange`. You call `setName`. React re-renders the component. The input displays the new value from state. Every keystroke goes through this cycle.

The consequence: at any point in time, `name` in state is the exact truth of what the input contains. You can read it, validate it, or clear it by setting state to `''`.

## Uncontrolled inputs

An uncontrolled input lets the DOM manage its own state. You read the value when you need it (typically on form submit) using a ref, rather than tracking every keystroke.

```jsx
function UncontrolledInput() {
  const inputRef = useRef(null);

  function handleSubmit(e) {
    e.preventDefault();
    console.log(inputRef.current.value);
  }

  return (
    <form onSubmit={handleSubmit}>
      <input ref={inputRef} defaultValue="" />
      <button type="submit">Submit</button>
    </form>
  );
}
```

Note `defaultValue` instead of `value`. `defaultValue` sets the initial value and lets the DOM manage it from there. Using `value` without `onChange` makes the input read-only (React will warn you).

## Why mixing them causes bugs

React tracks whether an input is controlled or uncontrolled based on whether the `value` prop is defined. The warning you'll see:

```
Warning: A component is changing an uncontrolled input to be controlled.
```

This happens when `value` starts as `undefined` and later becomes a string:

```jsx
// Bug: starts as undefined (uncontrolled), becomes '' (controlled)
function BuggyInput() {
  const [name, setName] = useState();
  // Initially: value={undefined} → uncontrolled
  // After any change: value={''} → controlled

  return (
    <input
      value={name}
      onChange={(e) => setName(e.target.value)}
    />
  );
}
```

Initialize state with an empty string, not `undefined`:

```jsx
const [name, setName] = useState(''); // Controlled from the start
```

The reverse also causes bugs: starting as controlled and dropping to uncontrolled when you pass `null`:

```jsx
// Bug
const [value, setValue] = useState('initial');
// Later: setValue(null)
// value={null} React treats as uncontrolled
```

Use empty string for "no value," not `null` or `undefined`.

## When to use each

**Use controlled inputs when:**
- You need to validate as the user types
- You need to derive values from input (character count, transformation)
- You need to enable/disable a submit button based on field values
- You need to programmatically clear or reset the input
- You have dependent fields (selecting a country filters available states)

```jsx
function SignUpForm() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const isValid = email.includes('@') && password.length >= 8;

  return (
    <form>
      <input value={email} onChange={e => setEmail(e.target.value)} />
      <input value={password} onChange={e => setPassword(e.target.value)} type="password" />
      <button disabled={!isValid}>Sign up</button>
    </form>
  );
}
```

**Use uncontrolled inputs when:**
- You have a simple form that only needs values on submit
- You are integrating with a non-React library that manages its own input state
- You need file inputs (file inputs are always uncontrolled in React)

```jsx
// File inputs are always uncontrolled
function FileUpload() {
  const fileRef = useRef(null);

  function handleSubmit() {
    const file = fileRef.current.files[0];
    uploadFile(file);
  }

  return (
    <>
      <input type="file" ref={fileRef} />
      <button onClick={handleSubmit}>Upload</button>
    </>
  );
}
```

## The read-only input

A `value` without `onChange` produces a read-only input and a React warning:

```jsx
// Warning: You provided a `value` prop without `onChange`
<input value="Fixed text" />

// Correct for truly read-only display:
<input value="Fixed text" readOnly />

// Or use defaultValue if you want the initial value but don't need to control it:
<input defaultValue="Starting text" />
```

## Resetting a form

Controlled forms reset by setting state back to initial values:

```jsx
function resetForm() {
  setName('');
  setEmail('');
  setMessage('');
}
```

Uncontrolled forms reset using the form element's `reset()` method:

```jsx
const formRef = useRef(null);

function handleReset() {
  formRef.current.reset();
}

return <form ref={formRef}>{/* inputs */}</form>;
```

For most React applications, controlled inputs are the standard approach. They integrate naturally with React's state model and make validation, conditional logic, and testing straightforward. Uncontrolled inputs are the exception, used in specific circumstances where reading on submit is sufficient.
