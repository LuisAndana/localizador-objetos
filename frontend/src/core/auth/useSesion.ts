import { useSyncExternalStore } from "react";
import { AUTENTICACION_ACTIVA, GRUPO_ADMINISTRADORES, suscribir, usuarioActual, type Usuario } from "./cognito";

/** Usuario con sesión, o null. Se actualiza al entrar, salir o caducar la sesión. */
export function useUsuario(): Usuario | null {
  return useSyncExternalStore(suscribir, usuarioActual, () => null);
}

/**
 * Si se muestran las acciones de administrador (eliminar, gestionar categorías).
 * Es solo para no ofrecer botones que fallarían: la API vuelve a comprobarlo.
 * En el modo local no hay usuarios, así que todo está disponible.
 */
export function useEsAdministrador(): boolean {
  const usuario = useUsuario();
  if (!AUTENTICACION_ACTIVA) return true;
  return usuario?.grupos.includes(GRUPO_ADMINISTRADORES) ?? false;
}
