---
title: "React Router nested routes: the layout pattern that removes repeated code."
description: "How to use nested routes in React Router v6 to share layouts across pages, eliminating duplicated navigation and wrapper components."
pubDate: 2024-11-28
tags: ["React"]
draft: false
---

Every multi-page React application has layouts: a navigation bar at the top, a sidebar, a footer, an authenticated wrapper. The naive approach repeats these in every page component. React Router's nested routes provide a better model: define the layout once, render child routes inside it, and let the router handle the composition.

## The problem with the flat approach

Without nested routes, you end up repeating layout components in every page:

```jsx
function Dashboard() {
  return (
    <>
      <NavBar />
      <Sidebar />
      <main>Dashboard content</main>
      <Footer />
    </>
  );
}

function Settings() {
  return (
    <>
      <NavBar />
      <Sidebar />
      <main>Settings content</main>
      <Footer />
    </>
  );
}

function Profile() {
  return (
    <>
      <NavBar />
      <Sidebar />
      <main>Profile content</main>
      <Footer />
    </>
  );
}
```

Every new page adds the same boilerplate. Changing the layout means touching every page.

## The nested route pattern

React Router v6 uses `<Outlet />` as a placeholder for child routes. The parent layout renders once and the child routes render in the Outlet's position.

```jsx
// AppLayout.jsx
import { Outlet } from 'react-router-dom';

function AppLayout() {
  return (
    <>
      <NavBar />
      <Sidebar />
      <main>
        <Outlet /> {/* Child routes render here */}
      </main>
      <Footer />
    </>
  );
}
```

Define the route hierarchy in your router configuration:

```jsx
import { createBrowserRouter, RouterProvider } from 'react-router-dom';

const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: 'settings', element: <Settings /> },
      { path: 'profile', element: <Profile /> },
    ],
  },
]);

function App() {
  return <RouterProvider router={router} />;
}
```

Now `Dashboard`, `Settings`, and `Profile` are simple components that only render their own content:

```jsx
function Dashboard() {
  return <div>Dashboard content</div>;
}

function Settings() {
  return <div>Settings content</div>;
}
```

The layout renders once. The Outlet swaps the child component as the user navigates. NavBar, Sidebar, and Footer are not re-rendered on route changes within this layout.

## Stacking multiple layouts

Nesting can go multiple levels deep. A common pattern is one layout for the public site and another for authenticated users:

```jsx
const router = createBrowserRouter([
  {
    path: '/',
    element: <PublicLayout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: 'about', element: <AboutPage /> },
      { path: 'login', element: <LoginPage /> },
    ],
  },
  {
    path: '/app',
    element: <AuthenticatedLayout />, // Checks auth, redirects if not logged in
    children: [
      { index: true, element: <Dashboard /> },
      { path: 'settings', element: <Settings /> },
      {
        path: 'projects',
        element: <ProjectsLayout />, // Another layout level with its own nav
        children: [
          { index: true, element: <ProjectList /> },
          { path: ':projectId', element: <ProjectDetail /> },
        ],
      },
    ],
  },
]);
```

Each layout in the chain renders an `<Outlet />`. The router resolves the full path and renders the appropriate chain of layouts and child components.

## The authenticated layout pattern

A common use of nested routes is protecting a section of the app:

```jsx
function AuthenticatedLayout() {
  const { user, isLoading } = useAuth();

  if (isLoading) return <LoadingSpinner />;
  if (!user) return <Navigate to="/login" replace />;

  return (
    <div className="app-shell">
      <NavBar user={user} />
      <main>
        <Outlet />
      </main>
    </div>
  );
}
```

Any route nested under this layout is automatically protected. No need to add auth checks to individual page components.

## Passing data from layout to child routes

Use `<Outlet />` with a `context` prop to pass values from the layout to child routes:

```jsx
function ProjectsLayout() {
  const { projectId } = useParams();
  const { data: project } = useFetch(`/api/projects/${projectId}`);

  return (
    <div>
      <ProjectHeader project={project} />
      <Outlet context={{ project }} /> {/* Pass project to all children */}
    </div>
  );
}

// In a child route
import { useOutletContext } from 'react-router-dom';

function ProjectDetail() {
  const { project } = useOutletContext();
  return <div>{project?.name}</div>;
}
```

## Using JSX-based route definitions

The object-based `createBrowserRouter` syntax is the current recommended approach, but if you prefer JSX, nested routes work the same way:

```jsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AppLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="settings" element={<Settings />} />
          <Route path="profile" element={<Profile />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
```

The `<Outlet />` in `AppLayout` renders whichever child route matches the current path.

The result is that layouts are defined exactly once. Adding a new page means creating a component and a route definition. No repeated wrapper code, no risk of inconsistencies between pages.
