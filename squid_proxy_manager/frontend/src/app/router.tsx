import { createBrowserRouter, RouterProvider } from 'react-router-dom';

import { getIngressBasename } from './ingress';

import { DashboardPage } from '@/features/instances/DashboardPage';
import { ProxyCreatePage } from '@/features/instances/ProxyCreatePage';
import { ProxyDetailsPage } from '@/features/instances/ProxyDetailsPage';
import { SettingsPage } from '@/features/instances/SettingsPage';

export function AppRouter() {
  const router = createBrowserRouter(
    [
      { path: '/', element: <DashboardPage /> },
      { path: '/proxies/new', element: <ProxyCreatePage /> },
      { path: '/proxies/:name', element: <ProxyDetailsPage /> },
      { path: '/settings', element: <SettingsPage /> }
    ],
    { basename: getIngressBasename() }
  );

  return <RouterProvider router={router} />;
}
