import { createBrowserRouter, RouterProvider } from 'react-router-dom';

import { getIngressBasename } from './ingress';

import { DashboardPage } from '@/features/instances/DashboardPage';
import { InstanceSettingsPage } from '@/features/instances/InstanceSettingsPage';
import { ProxyCreatePage } from '@/features/instances/ProxyCreatePage';

export function AppRouter() {
  const router = createBrowserRouter(
    [
      { path: '/', element: <DashboardPage /> },
      { path: '/proxies/new', element: <ProxyCreatePage /> },
      { path: '/proxies/:name/settings', element: <InstanceSettingsPage /> }
    ],
    { basename: getIngressBasename() }
  );

  return <RouterProvider router={router} />;
}
