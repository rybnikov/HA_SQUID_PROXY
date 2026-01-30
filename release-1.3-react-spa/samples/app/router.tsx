
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { getIngressBasename } from "./ingress";

// Pages (placeholder imports)
import { DashboardPage } from "../pages/DashboardPage";
import { ProxyCreatePage } from "../pages/ProxyCreatePage";
import { ProxyDetailsPage } from "../pages/ProxyDetailsPage";
import { SettingsPage } from "../pages/SettingsPage";

export function AppRouter() {
  const basename = getIngressBasename();

  const router = createBrowserRouter(
    [
      { path: "/", element: <DashboardPage /> },
      { path: "/proxies/new", element: <ProxyCreatePage /> },
      { path: "/proxies/:id", element: <ProxyDetailsPage /> },
      { path: "/settings", element: <SettingsPage /> },
    ],
    { basename }
  );

  return <RouterProvider router={router} />;
}
