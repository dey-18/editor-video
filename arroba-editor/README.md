# Arroba Editor 0.1.0 — primera versión local

**Aplicación activa:** editor nativo de Rust/Slint. Ábrelo con `Arroba Editor.lnk` en la carpeta `video-test`, o con `Arroba Editor.vbs` de esta carpeta. El lanzador utiliza copias versionadas del binario. El ejecutable de `dist/ArrobaEditor` y las instrucciones de Python/Tk de abajo corresponden al prototipo inicial, no al editor integrado actual. La hoja de ruta y estado actual están en `IMPLEMENTATION.md`.

Asistente de escritorio en español que automatiza el Concat instalado mediante su API MCP. Es una capa de automatización funcional: no reemplaza ni recompila la ventana del editor de Concat. La edición manual sigue haciéndose allí. Nombre provisional: Arroba Editor.

## Probar en Windows

1. Instala Concat 0.2.11 (ya instalado en este equipo).
2. Abre `ArrobaEditor.exe` dentro de la carpeta de distribución. Mantén `_internal` junto al ejecutable; el usuario no necesita Python ni herramientas de desarrollo.
3. Elige un video terminado. También puedes guardar tu carpeta de OBS y pulsar **Usar último video**.
4. Elige eliminación de silencios, pista de audio, subtítulos y zoom alterno opcional.
5. Pulsa **Preparar edición automática**.
6. Pulsa **Revisar en Concat** para corregir cortes/texto o **Exportar MP4** para obtener el video. Si el proyecto está abierto en Concat, guarda y cierra ese proyecto antes de exportar desde Arroba; también puedes exportar desde Concat.

El video original nunca se sobrescribe. Cada ejecución crea un proyecto nuevo con nombre único. Los clips referencian el video original: **no lo muevas ni lo borres** mientras quieras seguir editando. Los resultados quedan en la carpeta elegida, inicialmente `Videos/Arroba Editor`.

## Incluido

- Importación de archivos locales compatibles con Concat, incluidos MKV de OBS.
- Último video de una carpeta configurable (selección explícita; no vigila en segundo plano).
- Cortes no destructivos por volumen: Suave, Normal y Fuerte, con márgenes alrededor de la voz y límites alineados a fotogramas.
- Selección de una pista de audio, tanto para el análisis como para la edición/exportación.
- Subtítulos automáticos locales multilingües mediante Faster Whisper Tiny, en CPU/int8.
- Descarga explícita del modelo (~75 MB) una sola vez; después la transcripción funciona sin conexión.
- Importación de SRT sincronizado con el original y ajuste de sus tiempos a los cortes.
- Subtítulos editables en la línea de tiempo y copia en `arroba/subtitulos.srt`.
- Zoom alterno de 4 % en cada segundo fragmento, desactivado por defecto.
- Proyecto guardado para revisión manual en Concat y exportación H.264/MP4 mediante su motor.
- Progreso por etapas, cancelación, errores visibles, protección contra sobrescritura de exportaciones y reporte `arroba/resultado.json`.

## Límites de esta versión

- No incluye chat, cobros, cuentas, servicio alojado ni detección semántica de errores/repeticiones.
- Detecta silencio por volumen, no por comprensión del habla. Música o ruido pueden impedir cortes. Prueba Suave si una voz baja se corta demasiado.
- Usa **una sola pista de audio**. No mezcla todavía la voz y el escritorio de OBS: elige una pista que ya contenga la mezcla deseada.
- Tiny prioriza tamaño y rapidez; revisa nombres propios, acentos y puntuación. No se promete precisión perfecta.
- Un SRT externo se ajusta por intervalos, no por palabras: un subtítulo que cruza un corte puede repetirse en ambos lados.
- La carpeta no detecta automáticamente cuándo OBS termina. Elige una grabación finalizada. Se rechazan archivos que acaban de cambiar y se comprueba que no hayan cambiado durante el análisis.
- Los cambios del proyecto abierto en Concat no se modifican en vivo. El bloqueo del editor protege de escrituras concurrentes.
- Cancelar durante carga/inferencia del modelo o descarga puede esperar a que termine la operación interna actual. El cierre de la ventana espera al trabajador.
- Si un proceso falla, su carpeta se marca con `arroba/INCOMPLETO.txt`; no se presenta como resultado terminado.
- La primera versión conserva las dimensiones y fps del video. No convierte automáticamente a vertical.

## Desarrollo y pruebas

Python 3.13 x64, Concat 0.2.11 y Windows. No hace falta compilar Rust para esta capa.

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
.\.venv\Scripts\python.exe -m unittest -v test_engine
.\.venv\Scripts\python.exe integration_test.py
.\.venv\Scripts\python.exe app.py
.\.venv\Scripts\python.exe build.py
```

`integration_test.py` crea un MKV sintético con un silencio conocido y SRT; comprueba los cortes, los tiempos de origen, subtítulos, zoom, integridad del original y duración/audio del MP4 exportado. Sus archivos se guardan en `test-output/`.

`speech_test.py` verifica transcripción real con audio de muestra del repositorio, sin grabar ni enviar voz del usuario.

`--self-test <archivo.json>` en el ejecutable comprueba las dependencias empaquetadas sin mostrar la interfaz.

## Licencia y entrega del código

Esta capa se entrega bajo **AGPL-3.0-or-later**, con el texto de licencia y `SOURCE.zip` de su versión al lado del ejecutable. El código de Concat original está en este checkout y en https://github.com/jub0t/Concat; el binario 0.2.11 corresponde a https://github.com/jub0t/Concat/tree/v0.2.11.

Concat permanece instalado como componente independiente y sin modificar, con su nombre y avisos originales. Arroba Editor tiene su propio nombre y no se presenta como versión oficial de Concat. Consulta `THIRD_PARTY.md` para dependencias y pasos de distribución.

Esto es una entrega local de prueba, no una publicación comercial ni un instalador firmado. Antes de distribuir públicamente: preparar el instalador, comprobar las obligaciones de cada dependencia (incluido el código correspondiente de FFmpeg y bibliotecas), publicar el código de la versión ofrecida y revisar el flujo con videos reales. Los servicios y soporte pueden tener precio; los derechos AGPL del software se conservan.
