# Componentes externos

La prueba local utiliza estos componentes. `requirements.lock.txt` registra las versiones exactas y `DEPENDENCY-LICENSES.txt`, generado al empaquetar, conserva los avisos disponibles de los paquetes Python.

| Componente | Licencia / origen |
|---|---|
| Concat 0.2.11, instalado por separado | AGPL-3.0-or-later; https://github.com/jub0t/Concat/tree/v0.2.11. Conserva sus propios avisos en su carpeta de instalación. |
| Python / Tcl / Tk | PSF y licencias Tcl/Tk; los avisos del runtime se conservan en el paquete PyInstaller. |
| PyInstaller | GPL con excepción para el bootloader; https://github.com/pyinstaller/pyinstaller |
| Faster Whisper | MIT; https://github.com/SYSTRAN/faster-whisper |
| CTranslate2 | MIT; https://github.com/OpenNMT/CTranslate2 |
| Whisper Tiny convertido | https://huggingface.co/Systran/faster-whisper-tiny; modelo original Whisper MIT. Se descarga por separado; no se envían videos al proveedor. |
| imageio-ffmpeg | BSD-2-Clause; https://github.com/imageio/imageio-ffmpeg |
| FFmpeg incluido por imageio-ffmpeg | El ejecutable de esta instalación informa 9.0.2, Gyan essentials, `--enable-gpl --enable-version3`. GPLv3 o posterior según su configuración; https://www.gyan.dev/ffmpeg/builds/ y https://ffmpeg.org. |
| PyAV | BSD; bibliotecas FFmpeg enlazadas conservan sus propias licencias; https://github.com/PyAV-Org/PyAV |
| ONNX Runtime | MIT; https://github.com/microsoft/onnxruntime |
| Hugging Face Hub / Tokenizers | Apache-2.0; https://github.com/huggingface/huggingface_hub y https://github.com/huggingface/tokenizers |
| NumPy | BSD-3-Clause y avisos de bibliotecas incluidas; https://github.com/numpy/numpy |

No se ha reemplazado la licencia de ninguna dependencia. `SOURCE.zip` contiene el código propio y scripts de construcción; no pretende ser por sí solo el código correspondiente de cada dependencia nativa. Para una distribución pública se debe preparar también el acceso al código correspondiente de las versiones/configuraciones nativas redistribuidas, además de sus licencias. Esta carpeta es una compilación de prueba local.
