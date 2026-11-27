# Arroba Editor: especificación y plan de entrega

Estado: en implementación. Ninguna fase se considera terminada por tener código escrito: requiere ejecutar sus criterios de aceptación.

## Método

SDD (desarrollo guiado por especificación). Para operaciones críticas, pruebas antes de ampliar el comportamiento: límites de cortes, sincronización, cancelación y protección de originales. TDD complementa el trabajo; no exige pruebas que solo repitan colores o posiciones de controles. ODD no se usa como metodología porque su significado no se ha definido en este proyecto.

## Producto acordado

Una aplicación Windows con nombre propio, basada en Concat, con automatización y edición manual en la misma ventana. El usuario importa una grabación finalizada, elige acciones, obtiene un montaje editable, revisa y exporta. Posteriormente puede indicar acciones por chat. El código distribuido se ofrece bajo AGPL con avisos y fuentes correspondientes. Se cobra soporte y servicios; no se promete impedir modificaciones del cliente abierto.

## Fases y aceptación

### 1. Compilación reproducible del editor

- Usar el toolchain fijado por upstream y dependencias verificadas por SHA256.
- Registrar salida y código final; no confundir descarga con compilación exitosa.
- Aceptación: binario propio inicia, importa un video y exporta con audio.
- Estado: el fallo de ffmpeg-sys se resolvió cargando el entorno de Visual Studio. El editor nativo ya se ha compilado y ejecutado. La revisión actual incorpora confirmación de resultados, chat lateral y preparación con progreso; sigue pendiente su validación visual final.

### 2. Experiencia integrada y marca

- Inicio moderno: importar grabación, proyectos recientes y acceso a configuración.
- Flujo visible: Importar → Automatizar → Revisar → Exportar.
- Panel de automatización dentro de Slint, sin abrir el prototipo Tk como interfaz de producto.
- Mantener vista previa y línea de tiempo; controles avanzados disponibles al revisar.
- Mostrar progreso, cancelación, error recuperable y estado final; controles utilizables a 1366×768 y escalado 125 %.
- Nombre e icono propios; conservar atribuciones en Acerca de.
- Aceptación: una ventana permite completar el recorrido y volver a corregir sin perder trabajo. Revisión visual obligatoria del binario compilado.

### 3. Automatización nativa

- Importar MP4/MKV terminado y seleccionar pista de análisis.
- Detectar silencios con márgenes ajustables y cortes alineados a fotogramas.
- Aplicar comandos de edición en lote deshacible, guardando el proyecto.
- Transcribir con el subsistema nativo de Concat; subtítulos editables, tiempos ajustados al montaje.
- Zoom opcional sencillo; no afirmar que detecta momentos importantes.
- Preservar originales y comprobar cambios durante el procesamiento.
- Aceptación: casos sin silencio, silencio total, voz baja, varias pistas, fps fraccional, cancelación y error; comparar audio/video exportados. Probar una grabación real larga y registrar duración del proceso y memoria.
- Evidencia existente: prototipo externo pasa 11 pruebas, montaje/exportación sintética y transcripción real. Esto no demuestra todavía integración nativa.

### 4. Cuenta y derechos de servicio

- Servicio backend con autenticación mediante proveedor establecido; no inventar almacenamiento de contraseñas.
- Sesión protegida por almacenamiento seguro del sistema, cierre de sesión y recuperación.
- Servidor es autoridad de suscripción; nunca confiar en una variable Free/Pro del cliente.
- Modo local básico disponible sin conexión; límites y consumo de servicios se validan en servidor.
- Aceptación: usuario nuevo, sesión vencida, revocación, servicio caído, acceso cruzado rechazado y ausencia de secretos en binario/logs.
- Dependencias de lanzamiento: elegir proveedor, dominio y cuenta de despliegue. Preparar integración antes de pedir decisiones de publicación.

### 5. Planes y pagos

- Free: edición local básica. Pro: servicios de IA alojados, soporte y automatización avanzada según oferta final.
- Mostrar precio y límites reales; no incluir botones de compra que simulen cobro.
- Pagos mediante checkout alojado; webhooks firmados e idempotentes; cancelación y períodos de acceso definidos.
- Aceptación en entorno de pruebas: compra, renovación, fallo, cancelación, evento repetido y reversión. Publicar cobros reales requiere configuración y autorización final.

### 6. Chat de acciones

- Traducir instrucciones a un plan de acciones admitidas y mostrarlo antes de aplicar.
- Confirmar operaciones irreversibles; las ediciones ordinarias permanecen deshacibles.
- Tratar transcripciones y archivos como datos, nunca como instrucciones del sistema.
- Aceptación: solicitudes ambiguas piden precisión; acciones no soportadas no se anuncian como realizadas; deshacer recupera el proyecto.

### 7. Entrega

- Instalador, versión, actualización, fuentes correspondientes y avisos de dependencias.
- Publicar repositorio propio antes de distribuir una versión modificada a terceros.
- Verificar en Windows limpio sin herramientas de desarrollo, con y sin conexión.
- Entregar registro de pruebas, límites conocidos y guía de soporte.

## Regla de avance

Trabajar en orden. Comunicar avances observados y bloqueos concretos. Un proceso externo puede seguir después de una respuesta, pero la programación y supervisión del agente no continúan automáticamente entre mensajes. No anunciar fases pendientes como listas.

## Revisión de optimización, 27 de noviembre de 2026

- Implementado: caché del catálogo del motor con invalidación por versión y tiempo; resumen de la línea de tiempo activa; índice compacto de efectos con detalles de los más relevantes.
- Medición de la petición de título: catálogo completo 65.296 bytes; contexto reducido 8.771 bytes. Es una medida de bytes de contexto, no una promesa de latencia ni de ahorro exacto de tokens.
- Implementado: extracción de audio y detección de silencios en una sola pasada. La prueba de integración conserva los cortes esperados y exporta audio y video válidos.
- Implementado: devolución explícita de éxito/error del motor para Ruben-bot, detección de propuestas sin cambios y registro de aplicar, rechazar, deshacer y rehacer.
- Implementado: historial protegido frente a escrituras concurrentes; límite de 100 mensajes visibles y 16 mensajes de contexto; respuestas de otro proyecto no reemplazan el chat actual.
- Validado en interfaz con video sintético: panel lateral que reserva espacio al video; formulario de intensidad, pista, idioma y subtítulos; progreso por etapas; cancelación cooperativa; resumen antes de revisar el montaje.
- Implementado en el lanzador: copias versionadas del ejecutable para que una aplicación abierta no bloquee la siguiente compilación. Sigue siendo una instalación de desarrollo con dependencias locales; no equivale al instalador comercial.
- Pendiente: comparador original/resultado, selector de modelo local de mayor precisión, respuesta progresiva y cancelación de consultas del chat, lista de conversaciones, pruebas con grabaciones largas y preparación del instalador autocontenido. Cuentas, planes y pagos siguen pendientes de backend.

Validación: 36 pruebas locales correctas. OpenRouter propuso un título, el editor lo aplicó y deshizo; el historial registró ambas acciones. El flujo automático desde la interfaz produjo 7,4 s de un original de 10 s, con 2,6 s eliminados y dos fragmentos.
