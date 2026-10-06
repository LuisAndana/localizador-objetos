# Bitácora del equipo · Foráneos Team

Proyecto: Localizador inteligente de objetos para almacenes
Cómputo en la Nube, Grupo 501 · Universidad Autónoma de Sinaloa

> Esta bitácora se consolidó el 5 de octubre de 2026 a partir de los reportes de las prácticas, las actividades entregadas y el historial de commits del repositorio. A partir de esa fecha se actualiza en cada sesión de trabajo.

| Fecha | Qué se hizo | Evidencia |
|---|---|---|
| 2026-09-09 | **Día 0.** Apertura de la cuenta de AWS del equipo en el plan gratuito; crédito de 100 USD. | Reporte de la práctica 1 |
| 2026-09-10 | Presupuesto mensual con alertas por correo al 50 % y 80 %; crédito adicional de 20 USD (saldo: 120 USD). | Reporte de la práctica 1 |
| 2026-09-13 | Esquema de etiquetas (`Project`, `Team`, `Environment`) aplicado por primera vez y activado como etiquetas de asignación de costos. | Reporte de la práctica 1 |
| 2026-09-16 | Propuesta del proyecto: problema, usuarios, indicadores, arquitectura por capas, costos y plan de trabajo. | Propuesta del Localizador inteligente |
| 2026-09-17 | Políticas de identidad con mínimo privilegio por rol y rol de servicio `ForaneosTeam-Lambda-DynamoDB`. | Reporte de la práctica 2 |
| 2026-09-21 | Actividad de infraestructura global: región, zonas de disponibilidad y ubicaciones de borde. | Actividad del 21 de septiembre |
| 2026-09-22 | Revisión de los 6 pilares del marco de buena arquitectura; el pilar más débil es la operación (sin monitoreo ni alertas). | Actividad de los 6 pilares |
| 2026-09-23 | Primer servidor EC2 (t3.micro, Ubuntu 26.04) con rol `ForaneosTeam-EC2-DynamoDB`, grupo de seguridad y página con nginx; instancia detenida al cierre. | Reporte de la práctica 3 |
| 2026-09-30 | Sitio estático en el bucket `foraneos-team-sitio-01`: bloqueo público, política de solo lectura y regla de ciclo de vida. | Reporte de la práctica 4 |
| 2026-09-30 | Primer commit del repositorio `localizador-objetos`. | Historial de git |
| 2026-10-01 | Red `foraneos-vpc` (10.0.0.0/16) con dos subredes públicas y dos privadas; aislamiento de la privada comprobado con Reachability Analyzer; recursos de prueba eliminados. | Reporte de la práctica 5 |
| 2026-10-04 | Código base en el repositorio: API (20 funciones Lambda), app web, plantilla SAM y pruebas automatizadas; funciona en modo local. | Historial de git |
| 2026-10-05 | Inventario del repositorio y decisiones de alcance del E1: dos perfiles (administrador y operador), IA con Rekognition y Bedrock, prototipo virtual en esta asignatura. | Inventario del código; guía del E1 |
| 2026-10-06 | Entrega del E1 (anteproyecto). | Correo de entrega |

## Pendientes inmediatos

- [ ] Desplegar el stack en `us-east-1` (7 – 17 de octubre).
- [ ] Agregar `frontend/.env.production` al `.gitignore`.
- [ ] Comprobar el grupo `operadores` en la API (hoy solo se revisa `administradores`).
