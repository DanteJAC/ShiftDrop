# 🚩 Sistema de Banderas / Checkpoints (ShiftDrop)

Este archivo registra el historial de banderas del proyecto para permitir volver a cualquier estado previo de forma instantánea.

| Bandera | Tag Git | Descripción | Estado |
| :--- | :--- | :--- | :--- |
| **Bandera 1** | `bandera-1` | Estructura base del proyecto, entorno `uv`, dependencias y arquitectura inicial. | ✅ Completada |
| **Bandera 2** | `bandera-2` | Motores de conversión 100% locales con FFmpeg 7.1, Pillow, PyPDF y PyPDFium2. | ✅ Completada |
| **Bandera 3** | `bandera-3` | Sistema Radial Multinivel (Cascading Pie Menu) y guardado en la misma carpeta. | ✅ Completada |
| **Bandera 4** | `bandera-4` | Reconocimiento infalible de archivos en Windows (COM Shell + NoActivate) y ejecución total de opciones. | ✅ Completada |
| **Bandera 5** | `bandera-5` | Sistema Autónomo Integral: PDF ⇄ Word bidireccional, soporte total .txt (PDF vectorial ReportLab + Word .docx), multimedia FFmpeg, inspección magic bytes y 73 pruebas superadas. | ✅ Completada |
| **Bandera 6** | `bandera-6` | Ejecutable Windows independiente (.exe) empaquetado y verificado en `dist/ShiftDrop.exe` con icono nativo y dependencias incluidas. | ✅ Completada |
| **Bandera 7** | `bandera-7` | Soporte de Hojas de Cálculo (Excel .xlsx, .xls, .csv a PDF, Word, JSON, HTML) + Suite de Audio Avanzada (AIFF, WMA, AC3, AMR, control de velocidad x0.75 a x2.0) + Transcripción Offline (Whisper IA a TXT, SRT, DOCX). 95 pruebas al 100% y ejecutable actualizado. | ✅ Completada |
| **Bandera 8** | `bandera-8` | Estabilización, Seguridad y Optimización: Filtro de ventanas (sin interferencia en AutoCAD/Revit/Excel), aislamiento COM con DispatchEx y AutomationSecurity=3 (sin ejecución de macros ni cierre de Word del usuario), timeout ilimitado en FFmpeg, recorte WebM nativo (VP9/Opus), prevención de sobreescritura (archivo (1).ext), y distribución onedir ultrarrápida sin volcado en %TEMP% ni FFmpeg duplicado. 99 pruebas al 100%. | ✅ Activa |

---

### Instrucciones para restaurar:
Si solicitas *"Volvamos a la bandera X"*, se restaurará el estado del código correspondiente con `git checkout bandera-X`.
