// El simulador del nodo solo existe en el backend local; en AWS lo sustituye el ESP32 real.
export const DEMO_LOCAL = import.meta.env.VITE_DEMO_LOCAL !== "false";
