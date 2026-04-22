# Registro de Avances de Becarios

Este documento sirve como bitácora centralizada para que Patricio (Frontend) y Eluney (Backend) registren su progreso, decisiones técnicas y bloqueos de manera periódica.

## Sugerencias de uso
- Escribir entradas breves al finalizar la semana (o jornadas importantes).
- Incluir enlaces a PRs (Pull Requests) o commits relevantes.
- Mencionar si hubo alguna duda sobre el contrato de eventos o decisiones de diseño.

---

## Eluney (Backend / STT / Raspberry Pi)

### Semana 1
- **Fecha:** 15/04/2026
- **Avances:** 
  - Esta semana logre instalar todo lo necesario en la raspberry pi 4.
  - Realice el [benchmark de algunos modelos STT](https://github.com/cristianlukas/UNLZ-INCLU-IA/commit/e26be5b7767bd9594cc0fa6bc109846883d38f31), siendo faster_whisper tiny y vosk los más prometedores para subtitulado en tiempo real.
- **Problemas/Bloqueos:**
  - Detecte que desde telefonos los subtitulos se congelaban, pero desde PC se mostraban correctamente.
  - 

### Semana 2
- **Fecha:** DD/MM/AAAA
- **Avances:** 
- **Problemas/Bloqueos:**

---

## Patricio (Frontend / UX / Accesibilidad)

### Semana 1
- **Fecha:** 15/03/2026
- **Avances:** 
  - Cambios a nivel UI, accesibilidad y ajustes en el theme (6e45f7536efa3de85a37c03d7d5be359d9d85f6c)
- **Problemas/Bloqueos:**
  - Sin bloqueos

### Semana 2
- **Fecha:** 19/03/2026
- **Avances:**
  - Modificación para habilitar la app en modo PWA, además hice pruebas de carga, conectando multiples dispositivos (310efe287b506e0ad6c4ecfb8a8ebb3a3650bf82)
- **Problemas/Bloqueos:**
  - No logré que funcione la PWA desde fuera de localhost, hay un problema de certificados donde para ser PWA se requiere que la app se sirva a través de https, y no logré cargar correctamente el certificado

### Semana 3
- **Fecha:** DD/MM/AAAA
- **Avances:** 
- **Problemas/Bloqueos:**
