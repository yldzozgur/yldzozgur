---
title: "Formik + Yup: form validation that doesn't require 50 lines of state."
description: "How to use Formik for form state management and Yup for declarative validation schemas, replacing boilerplate useState and error-tracking logic with a clean, structured approach."
pubDate: 2024-12-09
tags: ["React"]
draft: false
---

Building forms from scratch in React means tracking field values, touched state, validation errors, and submit state separately. For a form with five fields, that's easily twenty `useState` calls and several `useEffect` hooks for validation. Formik manages all of this. Yup provides a declarative schema for the validation rules.

## What you'd write without them

```jsx
function RegistrationForm() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [emailError, setEmailError] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [emailTouched, setEmailTouched] = useState(false);
  const [passwordTouched, setPasswordTouched] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  function validate() {
    let valid = true;
    if (!email.includes('@')) {
      setEmailError('Invalid email');
      valid = false;
    }
    if (password.length < 8) {
      setPasswordError('Password must be at least 8 characters');
      valid = false;
    }
    return valid;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setEmailTouched(true);
    setPasswordTouched(true);
    if (!validate()) return;
    setIsSubmitting(true);
    await registerUser({ email, password });
    setIsSubmitting(false);
  }

  // ... render
}
```

This pattern scales poorly. Each new field multiplies the state and validation logic.

## The Formik + Yup version

```bash
npm install formik yup
```

```jsx
import { Formik, Form, Field, ErrorMessage } from 'formik';
import * as Yup from 'yup';

const validationSchema = Yup.object({
  email: Yup.string()
    .email('Invalid email address')
    .required('Email is required'),
  password: Yup.string()
    .min(8, 'Password must be at least 8 characters')
    .required('Password is required'),
});

function RegistrationForm() {
  return (
    <Formik
      initialValues={{ email: '', password: '' }}
      validationSchema={validationSchema}
      onSubmit={async (values, { setSubmitting }) => {
        await registerUser(values);
        setSubmitting(false);
      }}
    >
      {({ isSubmitting }) => (
        <Form>
          <div>
            <Field type="email" name="email" placeholder="Email" />
            <ErrorMessage name="email" component="p" />
          </div>
          <div>
            <Field type="password" name="password" placeholder="Password" />
            <ErrorMessage name="password" component="p" />
          </div>
          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Registering...' : 'Register'}
          </button>
        </Form>
      )}
    </Formik>
  );
}
```

Formik handles values, touched state, errors, and submission. Yup handles the validation rules. `ErrorMessage` renders an error only when the field has been touched and has a validation failure.

## How Yup schemas compose

Yup schemas are objects where each key maps to a chain of validation rules:

```jsx
const schema = Yup.object({
  username: Yup.string()
    .min(3, 'At least 3 characters')
    .max(20, 'No more than 20 characters')
    .matches(/^[a-zA-Z0-9_]+$/, 'Letters, numbers, and underscores only')
    .required('Required'),

  age: Yup.number()
    .min(18, 'Must be 18 or older')
    .max(120, 'Invalid age')
    .required('Required'),

  website: Yup.string()
    .url('Must be a valid URL')
    .nullable(), // Allows null values (optional field)

  confirmPassword: Yup.string()
    .oneOf([Yup.ref('password'), null], 'Passwords must match')
    .required('Required'),
});
```

`Yup.ref('password')` creates a reference to another field in the schema, useful for confirmation fields.

## Using the useFormik hook directly

For more control, use the `useFormik` hook instead of the render-prop API:

```jsx
import { useFormik } from 'formik';

function LoginForm() {
  const formik = useFormik({
    initialValues: { email: '', password: '' },
    validationSchema: Yup.object({
      email: Yup.string().email().required(),
      password: Yup.string().required(),
    }),
    onSubmit: async (values) => {
      await login(values);
    },
  });

  return (
    <form onSubmit={formik.handleSubmit}>
      <input
        name="email"
        value={formik.values.email}
        onChange={formik.handleChange}
        onBlur={formik.handleBlur}
      />
      {formik.touched.email && formik.errors.email && (
        <p>{formik.errors.email}</p>
      )}
      <input
        name="password"
        type="password"
        value={formik.values.password}
        onChange={formik.handleChange}
        onBlur={formik.handleBlur}
      />
      {formik.touched.password && formik.errors.password && (
        <p>{formik.errors.password}</p>
      )}
      <button type="submit" disabled={formik.isSubmitting}>
        Log in
      </button>
    </form>
  );
}
```

`handleChange` and `handleBlur` use the input's `name` attribute to know which field to update. `touched.fieldName` is set to `true` when the user leaves a field. Errors only display after the field has been touched, avoiding error messages before the user has had a chance to fill in the form.

## Controlling when validation runs

Formik validates on change, on blur, and on submit by default. You can turn off the first two for better performance on complex forms:

```jsx
<Formik
  validateOnChange={false}
  validateOnBlur={true}
  // ...
>
```

With only `validateOnBlur`, validation runs when the user moves focus away from a field and on submit. This reduces validation calls while still providing per-field feedback before submission.

## Setting field errors programmatically

After a form submission, the server may return field-specific errors (email already taken, username reserved). Formik provides `setFieldError` for this:

```jsx
onSubmit: async (values, { setFieldError, setSubmitting }) => {
  try {
    await registerUser(values);
  } catch (error) {
    if (error.field === 'email') {
      setFieldError('email', 'This email is already registered');
    }
  } finally {
    setSubmitting(false);
  }
}
```

The error appears in the same place as client-side validation errors, giving the user a consistent experience regardless of whether the error was caught client-side or server-side.
