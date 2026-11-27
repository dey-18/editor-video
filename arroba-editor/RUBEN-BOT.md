# Ruben-bot en el editor

Abre un proyecto y pulsa **Ruben-bot**, arriba a la derecha. Configura antes OpenRouter en **Cuenta e IA**, desde el inicio.

1. Escribe una petición concreta: «añade un título que diga Hola de 0 a 2 segundos» o «baja a 0.5 el volumen del clip c2».
2. **Enviar** transmite instrucciones, estado del proyecto y catálogo de efectos a OpenRouter y al proveedor del modelo. Puede consumir créditos.
3. Revisa la propuesta. **Aplicar cambios** ejecuta un lote de comandos en la sesión actual. Ctrl+Z lo deshace.
4. Revisa la vista previa y guarda/exporta con los controles normales del editor.

El proyecto permanece abierto. No se lo modifica mediante otro proceso ni se evade su bloqueo. El proceso auxiliar solo genera propuestas; la ventana valida los comandos tipados y los aplica. Si cambia el estado del proyecto mientras se consulta el modelo, se rechaza la propuesta antigua.

Herramientas iniciales: títulos, propiedades de clips (incluido texto y volumen), transformaciones, fotogramas clave y capas de efectos. No incluye ejecución de comandos del sistema, eliminación de archivos, exportación automática, cortes por chat ni una conversación persistente de varios turnos. Cada petición lee de nuevo el proyecto. Máximo ocho acciones por propuesta.

El primer panel muestra nombres técnicos y argumentos de las herramientas para poder revisar exactamente lo solicitado; falta una presentación más sencilla. No garantiza que el modelo interprete correctamente instrucciones ambiguas. Las propuestas pueden contener errores y requieren revisión.

Evidencia: `test_ruben_live.py` realiza una llamada real a OpenRouter con el proyecto sintético, valida la herramienta de título, aplica el comando y comprueba deshacer. No modifica ni guarda el proyecto del usuario. Las pruebas unitarias existentes cubren la lista de herramientas permitidas, el ámbito del proyecto y el procesamiento de subtítulos.
