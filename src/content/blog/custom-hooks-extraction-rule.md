---
title: "Custom hooks: the extraction rule that keeps them actually reusable."
description: "When to extract a custom hook, how to name and structure it for genuine reusability, and the mistakes that make custom hooks more complex than the code they replaced."
pubDate: 2024-11-21
tags: ["React"]
draft: false
---

Custom hooks are functions that start with `use` and can call other hooks. The naming convention is not cosmetic: it tells React's linter to apply hook rules to the function, and it signals to other developers that this function manages React state or effects.

The freedom to extract hooks is powerful. The trap is extracting them for the wrong reasons and ending up with abstractions that are harder to understand than the original code.

## The right reason to extract a custom hook

Extract a custom hook when you have **stateful logic that is genuinely shared between components**, or when a single component contains **multiple pieces of stateful logic that are cohesive but independent**.

The extraction rule: a hook should encapsulate a complete behavior, not just move code around.

### Shared logic between components

```jsx
// Before: duplicated in multiple components
function UserProfile() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch('/api/user')
      .then(res => res.json())
      .then(data => { setUser(data); setLoading(false); })
      .catch(err => { setError(err); setLoading(false); });
  }, []);

  // render...
}

// After: extracted to a hook
function useFetch(url) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    fetch(url)
      .then(res => res.json())
      .then(data => { if (!cancelled) { setData(data); setLoading(false); } })
      .catch(err => { if (!cancelled) { setError(err); setLoading(false); } });
    return () => { cancelled = true; };
  }, [url]);

  return { data, loading, error };
}

function UserProfile() {
  const { data: user, loading, error } = useFetch('/api/user');
  // render...
}
```

The hook encapsulates a complete fetch lifecycle. Any component that needs to fetch data can use it.

### Cohesive but distinct logic within one component

```jsx
// A form component before extraction
function RegistrationForm() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [usernameValid, setUsernameValid] = useState(true);
  const [passwordValid, setPasswordValid] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [windowWidth, setWindowWidth] = useState(window.innerWidth);

  useEffect(() => {
    const handler = () => setWindowWidth(window.innerWidth);
    window.addEventListener('resize', handler);
    return () => window.removeEventListener('resize', handler);
  }, []);

  // Lots more logic...
}
```

The window resize tracking is completely unrelated to the form logic. Extract it:

```jsx
function useWindowWidth() {
  const [width, setWidth] = useState(window.innerWidth);

  useEffect(() => {
    const handler = () => setWidth(window.innerWidth);
    window.addEventListener('resize', handler);
    return () => window.removeEventListener('resize', handler);
  }, []);

  return width;
}

function RegistrationForm() {
  const windowWidth = useWindowWidth();
  // Form logic, cleanly separated
}
```

## What makes a hook reusable vs tightly coupled

A reusable hook takes **generic inputs** and returns **generic outputs**. A tightly coupled hook is really just a component's logic with the JSX removed.

```jsx
// Tightly coupled: only works for one specific use case
function useUserProfileData() {
  const { id } = useParams(); // Coupled to routing
  const dispatch = useDispatch(); // Coupled to Redux
  const [user, setUser] = useState(null);

  useEffect(() => {
    fetchUser(id).then(user => {
      setUser(user);
      dispatch(setCurrentUser(user));
    });
  }, [id]);

  return user;
}

// More reusable: takes an ID, returns data and status
function useUser(userId) {
  const [user, setUser] = useState(null);
  const [status, setStatus] = useState('idle');

  useEffect(() => {
    if (!userId) return;
    setStatus('loading');
    fetchUser(userId)
      .then(data => { setUser(data); setStatus('success'); })
      .catch(() => setStatus('error'));
  }, [userId]);

  return { user, status };
}
```

The second version works anywhere. Pass it a user ID, get back a user and a status. The caller decides what to do with those values, including dispatching to Redux if needed.

## Naming

The name should describe **what the hook does**, not **which component uses it**. `useWindowWidth`, `useFetch`, `useDebounce`, `useLocalStorage` are good names. `useHomePageData`, `useProfileLogic`, `useFormStuff` are bad names.

Good names make the hook discoverable and signal what it can be reused for.

## The wrong reasons to extract a hook

**To reduce line count in a component.** Extracting five `useState` calls into a hook that returns all five setters saves no complexity. The component still manages the same state; the complexity is just hidden.

**To avoid thinking about where logic belongs.** If it's not clear whether logic belongs in the component, an effect, or an event handler, moving it to a hook doesn't resolve that uncertainty. Figure out the structure first.

**Because the component has too many hooks.** More hooks in a component is not itself a problem. If the hooks are all doing different things and all belong in the component, they should stay there.

The test: if you can't explain what problem the custom hook solves in one sentence, it's probably not the right abstraction yet.
