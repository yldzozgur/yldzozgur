---
title: "Form libraries: when Formik, React Hook Form, and none are each correct."
description: "A practical comparison of form handling approaches in React -- uncontrolled forms, React Hook Form, and Formik -- with guidance on when each makes sense."
pubDate: 2026-04-13
tags: ["Architecture"]
draft: false
---

Forms are where simple React state management meets validation, error handling, submission, and UX concerns. The range of approaches -- from plain HTML to full form libraries -- reflects that there's no universal right answer.

## The case for no library

For simple forms, a library adds overhead without adding much value. A contact form with three fields:

```tsx
function ContactForm() {
  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const data = new FormData(form);

    fetch('/api/contact', {
      method: 'POST',
      body: JSON.stringify({
        name: data.get('name'),
        email: data.get('email'),
        message: data.get('message'),
      }),
    });
  }

  return (
    <form onSubmit={handleSubmit}>
      <input name="name" required minLength={2} />
      <input name="email" type="email" required />
      <textarea name="message" required />
      <button type="submit">Send</button>
    </form>
  );
}
```

Native HTML validation (`required`, `type="email"`, `minLength`) handles basic validation. No library needed.

When you need inline validation messages, field-level errors, or complex business rules, you've outgrown uncontrolled forms.

## React Hook Form

React Hook Form (RHF) is built on uncontrolled inputs with a ref-based API. It re-renders as little as possible -- only fields with errors, not the whole form.

```tsx
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const schema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters'),
  email: z.string().email('Invalid email address'),
  age: z.number().min(18, 'Must be 18 or older'),
});

type FormData = z.infer<typeof schema>;

function RegistrationForm() {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const onSubmit = async (data: FormData) => {
    await createUser(data);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <input {...register('name')} />
      {errors.name && <p>{errors.name.message}</p>}

      <input {...register('email')} />
      {errors.email && <p>{errors.email.message}</p>}

      <input type="number" {...register('age', { valueAsNumber: true })} />
      {errors.age && <p>{errors.age.message}</p>}

      <button disabled={isSubmitting}>Submit</button>
    </form>
  );
}
```

`zodResolver` connects Zod schema validation to RHF. You define the schema once, get TypeScript types and validation for free.

RHF's performance advantage is real for large forms (many fields, nested structures). Because inputs are uncontrolled, typing in one field doesn't re-render other fields.

## Formik

Formik uses controlled inputs. Every keystroke triggers a state update and re-renders the form.

```tsx
import { Formik, Form, Field, ErrorMessage } from 'formik';
import * as Yup from 'yup';

const schema = Yup.object({
  name: Yup.string().min(2).required(),
  email: Yup.string().email().required(),
});

function RegistrationForm() {
  return (
    <Formik
      initialValues={{ name: '', email: '' }}
      validationSchema={schema}
      onSubmit={async values => {
        await createUser(values);
      }}
    >
      {({ isSubmitting }) => (
        <Form>
          <Field name="name" />
          <ErrorMessage name="name" />

          <Field name="email" type="email" />
          <ErrorMessage name="email" />

          <button disabled={isSubmitting}>Submit</button>
        </Form>
      )}
    </Formik>
  );
}
```

Formik has a gentler learning curve and a more ergonomic API for simple forms. The controlled approach means the form state is always in sync with React state, which can simplify conditional rendering logic.

The downside is performance on large forms. Each keystroke re-renders the form. For most forms (under 20 fields), this is imperceptible. For very large, complex forms, it's a real issue.

## The framework option

Next.js Server Actions + `useFormState` handle forms without client-side form libraries at all:

```tsx
// Server Action
async function submitForm(prevState: any, formData: FormData) {
  'use server';
  // validate, mutate, return state
}

// Client component
'use client';
import { useFormState } from 'react-dom';

function Form() {
  const [state, action] = useFormState(submitForm, {});
  return <form action={action}>...</form>;
}
```

No library dependency, progressive enhancement, and server-side validation. Limited to simpler forms without complex client-side UX requirements.

## Summary

| Scenario | Recommendation |
|----------|---------------|
| Simple form, basic validation | No library (HTML5 constraints) |
| Complex validation, many fields | React Hook Form + Zod |
| Team already using Formik, moderate complexity | Formik + Yup |
| Next.js, server-rendered, no complex client UX | Server Actions |
| Very large dynamic forms | React Hook Form (performance) |
