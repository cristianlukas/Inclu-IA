# Guia de trabajo para Eluney Luna

Este documento es para **Eluney Luna**.

No corresponde a Patricio Garces.
Patricio trabaja frontend y no necesita seguir esta guia.

Objetivo: medir y dejar documentado el comportamiento de STT en **Raspberry Pi 4 Model B 8GB** trabajando en **espanol**.

## Orden de lectura obligatorio

1. `docs/plan_eluney_backend.md`
2. `docs/instalacion.md`
3. `docs/uso.md`
4. `docs/troubleshooting.md`
5. `docs/benchmark_raspi4_es.md`
6. `docs/benchmark_alt_asr_es.md`

## Regla de trabajo

- No sacar conclusiones desde pruebas con microfono si antes no corriste pruebas con archivo.
- Primero comparar modelos con audios repetibles.
- Despues recien probar microfono real.
- Idioma fijo: `es`.
- En Linux, ejecutar scripts con `bash scripts/...`, no con `sh scripts/...`.

## Entorno objetivo

- Preparacion local opcional: Windows 11.
- Entorno real de despliegue: Raspberry Pi OS 64-bit.
- Hardware objetivo: Raspberry Pi 4 Model B 8GB.

## Paso 1: preparar la Raspberry Pi

Desde la Pi:

```bash
cd /home/pi
git clone <URL-DEL-REPO> UNLZ-INCLU-IA
cd /home/pi/UNLZ-INCLU-IA
sudo apt update
sudo apt install -y curl python3 python3-venv python3-pip ffmpeg
bash scripts/install_backend.sh
```

Verificacion minima:

```bash
cd /home/pi/UNLZ-INCLU-IA/software
source .venv/bin/activate
python -m pytest -q
```

Esperado: tests en verde.

## Paso 2: bajar audios de prueba en espanol

```bash
cd /home/pi/UNLZ-INCLU-IA
bash scripts/download_test_audio.sh
```

Archivos esperados:

- `assets/test_audio/es/SpanishL1D1.ogg`
- `assets/test_audio/es/SpanishL1D2.ogg`
- `assets/test_audio/es/Siqueresirte_v1.ogg`

## Paso 3: correr benchmark de modelos

```bash
cd /home/pi/UNLZ-INCLU-IA
bash scripts/run_benchmark_raspi4_es.sh
```

Archivo de salida esperado:

- `software/benchmark_results/pi4_faster_whisper_es.json`

## Paso 3.1: correr alternativas a Whisper

Instalacion:

```bash
cd /home/pi/UNLZ-INCLU-IA
source software/.venv/bin/activate
pip install -r software/requirements-alt-asr.txt
bash scripts/download_vosk_es_model.sh
```

Moonshine:

```bash
cd /home/pi/UNLZ-INCLU-IA/software
source .venv/bin/activate
python tools/benchmark_moonshine.py \
  --manifest ../assets/test_audio/es/manifest.json \
  --audio-dir ../assets/test_audio/es \
  --output ./benchmark_results/pi4_moonshine_es.json
```

Vosk:

```bash
cd /home/pi/UNLZ-INCLU-IA/software
source .venv/bin/activate
python tools/benchmark_vosk.py \
  --manifest ../assets/test_audio/es/manifest.json \
  --audio-dir ../assets/test_audio/es \
  --model-path ../assets/models/vosk/vosk-model-small-es-0.42 \
  --output ./benchmark_results/pi4_vosk_es.json
```

## Paso 4: como interpretar el benchmark

Campos clave:

- `realtime_factor`: si es menor que `1.0`, va mas rapido que tiempo real.
- `expected_token_recall`: cuantas palabras esperadas recupera el modelo.

Decision practica:

- Si `base` mantiene mejor texto y no se va mucho de tiempo real, usar `base`.
- Si `small` mejora poco pero tarda mucho mas, descartarlo para vivo.
- Si `base` queda demasiado lento en la Pi con microfono, bajar a `tiny`.

## Paso 5: configurar prueba con microfono real

Editar:

- `software/.env`

Base recomendada:

```env
INCLUIA_DRIVER=faster_whisper
INCLUIA_FW_MODEL=base
INCLUIA_FW_COMPUTE_TYPE=int8
INCLUIA_FW_LANGUAGE=es
INCLUIA_FW_PHRASE_LIMIT_S=3
INCLUIA_FW_VAD=1
INCLUIA_FW_QUEUE_MAX_CHUNKS=6
```

Si el adaptador USB no trabaja bien a 16000 Hz:

```env
INCLUIA_AUDIO_SAMPLE_RATE=48000
```

Si necesitas fijar un dispositivo:

```env
INCLUIA_AUDIO_DEVICE_INDEX=0
```

Antes de definirlo, listar dispositivos:

```bash
cd /home/pi/UNLZ-INCLU-IA/software
source .venv/bin/activate
python tools/list_audio_devices.py
```

## Paso 6: prueba manual del backend

```bash
cd /home/pi/UNLZ-INCLU-IA/software
source .venv/bin/activate
python server.py --driver faster_whisper
```

Verificar:

- `http://127.0.0.1:5000/_health`
- estado en consola
- que no aparezcan errores de audio

## Paso 7: prueba larga

Hacer una prueba de 20 a 30 minutos y anotar:

- modelo usado
- sample rate usado
- microfono/adaptador usado
- latencia percibida
- cortes o cuelgues
- calidad de transcripcion

Registrar eso en:

- `docs/registro_avances.md`

## Paso 8: protocolo especifico de streaming (obligatorio)

Contexto:

- el driver `faster_whisper` ahora usa captura continua en background + cola de chunks
- eso evita el bloqueo de captura durante transcripcion

Objetivo de la prueba:

- validar que no se frene el flujo de subtitulos en sesiones de 20 min
- medir si la cola se satura y con que frecuencia

### Perfil 1 (recomendado inicial Pi 4)

```env
INCLUIA_DRIVER=faster_whisper
INCLUIA_FW_MODEL=base
INCLUIA_FW_COMPUTE_TYPE=int8
INCLUIA_FW_LANGUAGE=es
INCLUIA_FW_PHRASE_LIMIT_S=3
INCLUIA_FW_VAD=1
INCLUIA_FW_QUEUE_MAX_CHUNKS=6
```

### Perfil 2 (fallback conservador)

```env
INCLUIA_DRIVER=faster_whisper
INCLUIA_FW_MODEL=tiny
INCLUIA_FW_COMPUTE_TYPE=int8
INCLUIA_FW_LANGUAGE=es
INCLUIA_FW_PHRASE_LIMIT_S=4
INCLUIA_FW_VAD=1
INCLUIA_FW_QUEUE_MAX_CHUNKS=8
```

### Ejecucion y observacion

1. Correr backend:

```bash
cd /home/pi/UNLZ-INCLU-IA/software
source .venv/bin/activate
python server.py --driver faster_whisper
```

2. Mantener lectura continua 20 minutos (ritmo normal de clase).
3. Mirar logs y contar apariciones de:
- `Audio en cola saturado: se descartaron chunks viejos para mantener streaming`
4. Validar desde celular:
- que no se congelen subtitulos
- que no haya pausas largas repetidas

### Criterio rapido de decision

- Si Perfil 1 no satura (o satura muy poco), mantener Perfil 1.
- Si Perfil 1 satura seguido, usar Perfil 2 para demo estable.
- Si ambos saturan mucho, pasar a `whisper_cpp` para clase en vivo y dejar `faster_whisper` para respaldo.

### Plantilla minima para registrar en `docs/registro_avances.md`

- fecha
- perfil usado (1 o 2)
- microfono/adaptador
- duracion total (min)
- cantidad de eventos \"cola saturada\"
- percepcion de latencia (baja/media/alta)
- decision (seguir / ajustar / cambiar driver)

## Recomendacion inicial para tu hardware

Para **Raspberry Pi 4 Model B 8GB**:

- Empezar con `base`
- Mantener idioma fijo `es`
- Probar `small` solo como comparativa
- Usar `tiny` si `base` no da tiempo real con microfono

## Errores comunes

- Probar solo con microfono y sin benchmark por archivo
- Cambiar varias variables a la vez y no saber que mejoro o empeoro
- Dejar autodeteccion de idioma
- Sacar conclusiones desde Windows 11 y asumir que la Pi va a rendir igual

## Entregable minimo esperado de Eluney Luna

Antes de cerrar esta etapa, dejar documentado:

1. Resultado de `tiny`, `base` y `small` en la Pi.
2. Resultado de `Moonshine` y `Vosk` en la Pi.
3. Driver/modelo recomendado para demo real.
4. Configuracion valida de microfono.
5. Problemas encontrados y mitigacion.
