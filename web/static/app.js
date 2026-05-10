(() => {
  const appEl = document.querySelector(".app");
  const statusPill = document.getElementById("statusPill");
  const networkHint = document.getElementById("networkHint");
  const onboardingText = document.getElementById("onboardingText");
  const liveCaption = document.getElementById("liveCaption");
  const historyList = document.getElementById("historyList");
  const sourceTag = document.getElementById("sourceTag");
  const fontSize = document.getElementById("fontSize");
  const contrastMode = document.getElementById("contrastMode");
  const clearBtn = document.getElementById("clearBtn");
  const menuToggle = document.getElementById("menuToggle");
  const modeHint = document.getElementById("modeHint");
  const modeLiveBtn = document.getElementById("modeLiveBtn");
  const modeDemoBtn = document.getElementById("modeDemoBtn");
  const modeReplayBtn = document.getElementById("modeReplayBtn");

  const DEMO_LINES = [
    "Bienvenidos a Inclu-IA.",
    "Este es un subtitulo simulado para validar lectura.",
    "Modo demo activo, no depende del backend STT.",
    "Puedes usar replay para revisar frases anteriores.",
  ];

  const MODES = {
    LIVE: "live",
    DEMO: "demo",
    REPLAY: "replay",
  };

  let socket = null;
  let currentMode = MODES.LIVE;
  let demoInterval = null;
  let replayInterval = null;
  let lastHistoryItems = [];
  let lastConfig = null;

  const savedFont = localStorage.getItem("incluia_font");
  if (savedFont && ["s", "m", "l"].includes(savedFont)) {
    appEl.dataset.font = savedFont;
    fontSize.value = savedFont;
  }

  const savedTheme = localStorage.getItem("incluia_theme");
  if (savedTheme === "contrast") {
    appEl.dataset.theme = "contrast";
  } else if (savedTheme === "oled") {
    appEl.dataset.theme = "oled";
  }

  contrastMode.value =
    savedTheme === "light" ? "normal" : savedTheme === "contrast" ? "high" : "oled";

  const fmtTime = (ms) => {
    if (!ms) return "";
    try {
      return new Date(ms).toLocaleTimeString();
    } catch {
      return "";
    }
  };

  const setStatus = (stateName, detail = "") => {
    const map = {
      idle: "Idle",
      listening: "Escuchando",
      transcribing: "Transcribiendo",
      error: "Error",
      demo: "Demo",
      replay: "Replay",
    };

    const label = map[stateName] || stateName || "Desconocido";
    statusPill.textContent = detail ? `${label}: ${detail}` : label;

    if (stateName === "error") {
      statusPill.style.background = "#ffe8e8";
      statusPill.style.color = "#8e1f1f";
      return;
    }

    statusPill.style.background = "";
    statusPill.style.color = "";
  };

  const clearHistoryUI = () => {
    historyList.innerHTML = "";
  };

  const appendHistoryItem = (caption) => {
    const item = document.createElement("li");
    item.className = "history-item";

    const ts = document.createElement("span");
    ts.className = "item-time";
    ts.textContent = fmtTime(caption.t_server_ms);

    const content = document.createElement("span");
    content.textContent = caption.text;

    item.appendChild(ts);
    item.appendChild(content);
    historyList.insertBefore(item, historyList.firstChild);

    if (historyList.children.length > 300) {
      historyList.removeChild(historyList.lastElementChild);
    }
  };

  const onCaption = (caption) => {
    if (!caption || !caption.text) return;

    if (caption.source) {
      sourceTag.textContent = `source: ${caption.source}`;
    }

    if (caption.is_final) {
      appendHistoryItem(caption);
      liveCaption.textContent = caption.text;
      return;
    }

    liveCaption.textContent = caption.text;
  };

  const setModeUI = (mode) => {
    modeLiveBtn.classList.toggle("active", mode === MODES.LIVE);
    modeDemoBtn.classList.toggle("active", mode === MODES.DEMO);
    modeReplayBtn.classList.toggle("active", mode === MODES.REPLAY);

    const map = {
      [MODES.LIVE]: "En vivo",
      [MODES.DEMO]: "Demo",
      [MODES.REPLAY]: "Replay",
    };
    modeHint.textContent = map[mode] || "Auto";
  };

  const stopAllIntervals = () => {
    if (demoInterval) clearInterval(demoInterval);
    if (replayInterval) clearInterval(replayInterval);
    demoInterval = null;
    replayInterval = null;
  };

  const updateOnboarding = (cfg) => {
    const url = cfg?.ap_url || window.location.origin;
    const ssid = cfg?.ap_ssid || "Inclu-IA-AP";
    onboardingText.innerHTML = `1) Conectate a <strong>${ssid}</strong>. 2) Abrí <strong>${url}</strong>. 3) Esperá estado "Escuchando".`;
  };

  const startDemoMode = () => {
    stopAllIntervals();
    currentMode = MODES.DEMO;
    setModeUI(currentMode);
    setStatus("demo", "Subtitulos simulados");
    sourceTag.textContent = "source: demo";
    networkHint.textContent = "Modo demo local (sin backend)";

    let idx = 0;
    demoInterval = setInterval(() => {
      const text = DEMO_LINES[idx % DEMO_LINES.length];
      idx += 1;

      onCaption({
        text,
        is_final: false,
        t_server_ms: Date.now(),
        source: "demo",
      });

      setTimeout(() => {
        onCaption({
          text,
          is_final: true,
          t_server_ms: Date.now(),
          source: "demo",
        });
      }, 900);
    }, 2300);
  };

  const startReplayMode = () => {
    stopAllIntervals();
    currentMode = MODES.REPLAY;
    setModeUI(currentMode);
    setStatus("replay", "Reproduciendo historial");
    sourceTag.textContent = "source: replay";

    const items = [...lastHistoryItems].reverse();
    if (!items.length) {
      liveCaption.textContent = "Sin historial para replay. Cambiá a demo o en vivo.";
      return;
    }

    let idx = 0;
    replayInterval = setInterval(() => {
      const item = items[idx % items.length];
      idx += 1;
      onCaption({
        text: item.text,
        is_final: true,
        t_server_ms: Date.now(),
        source: "replay",
      });
    }, 1800);
  };

  const startLiveMode = () => {
    stopAllIntervals();
    currentMode = MODES.LIVE;
    setModeUI(currentMode);
    networkHint.textContent = "Conectando con servidor en vivo...";
    connectSocket(lastConfig);
  };

  const loadConfig = async () => {
    try {
      const response = await fetch("/api/config");
      if (!response.ok) return null;
      const cfg = await response.json();
      lastConfig = cfg;

      const url = cfg.ap_url || window.location.origin;
      const ssid = cfg.ap_ssid ? `Conectate al WiFi: ${cfg.ap_ssid}` : "WiFi local";
      networkHint.textContent = `${ssid} | URL: ${url}`;
      sourceTag.textContent = `source: ${cfg.active_source || "-"}`;
      updateOnboarding(cfg);
      return cfg;
    } catch {
      networkHint.textContent = "Sin acceso a /api/config. Usando modo local.";
      updateOnboarding(null);
      return null;
    }
  };

  const loadHistory = async () => {
    try {
      const response = await fetch("/api/history");
      if (!response.ok) return;
      const payload = await response.json();
      lastHistoryItems = Array.isArray(payload.items) ? payload.items : [];
    } catch {
      lastHistoryItems = [];
    }
  };

  const connectSocket = (cfg = null) => {
    if (currentMode !== MODES.LIVE) return;

    if (typeof io !== "function") {
      startDemoMode();
      return;
    }

    if (socket) {
      socket.off();
      socket.disconnect();
      socket = null;
    }

    const transport = cfg?.socket_transport || "polling";
    const socketOptions = {
      reconnection: true,
      reconnectionAttempts: Infinity,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      timeout: 10000,
    };

    if (transport === "polling") {
      socketOptions.transports = ["polling"];
      socketOptions.upgrade = false;
    } else if (transport === "websocket") {
      socketOptions.transports = ["websocket"];
      socketOptions.upgrade = false;
    }

    socket = io(socketOptions);

    socket.on("connect", () => {
      if (currentMode !== MODES.LIVE) return;
      setStatus("idle", "Conectado");
      networkHint.textContent = "Conectado al servidor en vivo.";
    });

    socket.on("disconnect", () => {
      if (currentMode !== MODES.LIVE) return;
      setStatus("error", "Desconectado. Reintentando...");
      networkHint.textContent = "Se perdió conexión. Reintentando...";
    });

    socket.on("connect_error", (err) => {
      if (currentMode !== MODES.LIVE) return;
      setStatus("error", "Servidor no disponible");
      networkHint.textContent = `Error de conexión: ${err?.message || "desconocido"}`;
    });

    socket.on("status", (payload) => {
      if (currentMode !== MODES.LIVE || !payload) return;
      setStatus(payload.state, payload.detail);
    });

    socket.on("caption", (caption) => {
      if (currentMode !== MODES.LIVE) return;
      onCaption(caption);
      if (caption?.is_final) {
        lastHistoryItems.unshift(caption);
        if (lastHistoryItems.length > 300) lastHistoryItems.length = 300;
      }
    });

    socket.on("history", (payload) => {
      if (currentMode !== MODES.LIVE) return;
      clearHistoryUI();
      const items = payload && Array.isArray(payload.items) ? payload.items : [];
      lastHistoryItems = [...items];
      items.forEach((item) => appendHistoryItem(item));
    });

    socket.on("history_cleared", () => {
      clearHistoryUI();
      liveCaption.textContent = "";
      lastHistoryItems = [];
    });
  };

  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("/static/serviceWorker.js").catch(() => {
        // Best effort only.
      });
    });
  }

  fontSize.addEventListener("change", () => {
    appEl.dataset.font = fontSize.value;
    localStorage.setItem("incluia_font", fontSize.value);
  });

  contrastMode.addEventListener("change", (e) => {
    const value = e.target.value;
    let theme = "light";
    if (value === "high") theme = "contrast";
    if (value === "oled") theme = "oled";
    appEl.dataset.theme = theme;
    localStorage.setItem("incluia_theme", theme);
  });

  clearBtn.addEventListener("click", async () => {
    clearHistoryUI();
    liveCaption.textContent = "";
    lastHistoryItems = [];

    if (socket && currentMode === MODES.LIVE) {
      socket.emit("clear_history");
    }

    try {
      await fetch("/api/clear", { method: "POST" });
    } catch {
      // Best effort only.
    }
  });

  menuToggle.addEventListener("click", () => {
    menuToggle.parentElement.classList.toggle("open");
  });

  modeLiveBtn.addEventListener("click", () => {
    startLiveMode();
  });

  modeDemoBtn.addEventListener("click", () => {
    startDemoMode();
  });

  modeReplayBtn.addEventListener("click", () => {
    startReplayMode();
  });

  Promise.all([loadConfig(), loadHistory()]).then(([cfg]) => {
    setModeUI(currentMode);
    connectSocket(cfg);
  });
})();
