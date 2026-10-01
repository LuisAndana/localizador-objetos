import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router";
import "@fontsource-variable/inter";
import "@/styles/index.css";
import { Providers } from "@/app/providers";
import { router } from "@/app/router";

// Tema antes del primer render para evitar el destello claro→oscuro.
try {
  const tema = localStorage.getItem("tema");
  const prefiereOscuro = window.matchMedia("(prefers-color-scheme: dark)").matches;
  if (tema === "oscuro" || (!tema && prefiereOscuro)) document.documentElement.classList.add("dark");
} catch {
  /* sin almacenamiento disponible: se usa el tema claro */
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Providers>
      <RouterProvider router={router} />
    </Providers>
  </StrictMode>,
);
