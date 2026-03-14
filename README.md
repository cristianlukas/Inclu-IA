![Logo Institucional](https://github.com/JonatanBogadoUNLZ/PPS-Jonatan-Bogado/blob/9952aac097aca83a1aadfc26679fc7ec57369d82/LOGO%20AZUL%20HORIZONTAL%20-%20fondo%20transparente.png)

# Universidad Nacional de Lomas de Zamora - Facultad de Ingeniería
# Inclu-IA

Inclu-IA es un appliance de subtitulado en tiempo real para aula.

Objetivo: una Raspberry Pi capta audio (microfono inalambrico), transcribe localmente y publica subtitulos en una web local para estudiantes con sordera o hipoacusia.

## Estado del repositorio

Este repositorio queda listo como base de trabajo para dos perfiles en paralelo:

- Backend (Eluney): servicio de transcripcion, red AP y operacion en Raspberry Pi.
- Frontend (Patricio): UI web mobile-first para subtitulos en vivo.

Incluye:

- Backend Flask + Flask-SocketIO con contrato de eventos estable.
- Drivers de transcripcion desacoplados (`simulator`, `faster_whisper`, `whisper_cpp`).
- Frontend accesible con reconexion, historial, tamano de fuente y alto contraste.
- Configuracion de red AP (`hostapd`, `dnsmasq`) y scripts de instalacion.
- Documentacion de instalacion, uso, troubleshooting y plan de trabajo.

## Documentacion clave para becarios

Leer en este orden:

1. [`docs/plan_becarios.md`](docs/plan_becarios.md)
2. [`docs/plan_eluney_backend.md`](docs/plan_eluney_backend.md)
3. [`docs/plan_patricio_frontend.md`](docs/plan_patricio_frontend.md)
4. [`docs/contrato_eventos.md`](docs/contrato_eventos.md)
5. [`docs/instalacion.md`](docs/instalacion.md)
6. [`docs/uso.md`](docs/uso.md)

`docs/plan_becarios.md` deja explicitamente documentado:

- el objetivo final,
- lo que ya esta hecho,
- el plan paralelo no bloqueante para Patricio y Eluney.

## Estructura

```text
Inclu-IA/
├── README.md
├── LICENSE
├── hardware/
│   └── esquemas_diagrama.md
├── software/
│   ├── server.py
│   ├── requirements.txt
│   ├── config/
│   │   ├── hostapd.conf
│   │   └── dnsmasq.conf
│   ├── incluia/
│   │   ├── app.py
│   │   ├── config.py
│   │   ├── events.py
│   │   └── transcribers/
│   └── tests/
├── web/
│   ├── templates/
│   │   └── index.html
│   └── static/
│       ├── app.js
│       └── styles.css
├── scripts/
│   ├── install_backend.sh
│   ├── setup_ap_networkmanager.sh
│   ├── setup_ap_hostapd_dnsmasq.sh
│   └── download_models.sh
├── deploy/
│   └── inclu-ia.service
└── docs/
    ├── instalacion.md
    ├── uso.md
    ├── troubleshooting.md
    ├── contrato_eventos.md
    ├── plan_becarios.md
    ├── plan_eluney_backend.md
    └── plan_patricio_frontend.md
```

## Quick start local (sin hardware)

1. Crear entorno virtual e instalar dependencias:

```bash
cd software
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Levantar servidor en modo simulador (default):

```bash
python server.py
```

3. Abrir:

- `http://127.0.0.1:5000`

La UI recibe subtitulos simulados por Socket.IO y permite validar flujo frontend/backend.

## Quick start Raspberry Pi

1. Configurar AP (recomendado NetworkManager):

```bash
sudo bash scripts/setup_ap_networkmanager.sh
```

2. Instalar backend:

```bash
sudo bash scripts/install_backend.sh
```

3. Configurar `.env`/variables de servicio para elegir driver STT:

- `INCLUIA_DRIVER=simulator` (desarrollo)
- `INCLUIA_DRIVER=faster_whisper` (pipeline Python)
- `INCLUIA_DRIVER=whisper_cpp` (pipeline CLI)

4. Iniciar servicio:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now inclu-ia.service
```

5. Desde un celular conectado al AP, abrir:

- `http://192.168.4.1:5000`
- o `http://inclu-ia.local:5000` (si mDNS esta activo)

## Contrato backend/frontend

Eventos Socket.IO emitidos por backend:

- `status`: `{ state, detail, t_server_ms }`
- `caption`: `{ id, text, t0_ms, t1_ms, is_final, t_server_ms, source }`
- `history`: `{ items: Caption[] }`
- `history_cleared`: `{ t_server_ms }`

Detalles en [`docs/contrato_eventos.md`](docs/contrato_eventos.md).

## Criterios de MVP aula

- AP levantado en Raspberry Pi.
- 3 o mas celulares recibiendo subtitulos en simultaneo.
- Reconexion sin romper el stream.
- Modo de operacion sin internet.

## Siguientes pasos recomendados

1. Ejecutar semana 1 del plan en [`docs/plan_becarios.md`](docs/plan_becarios.md).
2. Medir latencia real en Pi 4 y Pi 5 para fijar driver por defecto.
3. Ajustar chunking/VAD con pruebas de aula real.

## Licencia

MIT. Ver [`LICENSE`](LICENSE).
