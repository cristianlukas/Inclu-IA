(() => {
  const appEl = document.querySelector(".app");
  const statusPill = document.getElementById("statusPill");
  const networkHint = document.getElementById("networkHint");
  const liveCaption = document.getElementById("liveCaption");
  const historyList = document.getElementById("historyList");
  const sourceTag = document.getElementById("sourceTag");
  const fontSize = document.getElementById("fontSize");
  const contrastToggle = document.getElementById("contrastToggle");
  const clearBtn = document.getElementById("clearBtn");
  const menuToggle = document.getElementById("menuToggle");

  const state = {
    latestSource: "-",
  };

  const savedFont = localStorage.getItem("incluia_font");
  if (savedFont && ["s", "m", "l"].includes(savedFont)) {
    appEl.dataset.font = savedFont;
    fontSize.value = savedFont;
  }

  const savedTheme = localStorage.getItem("incluia_theme");
  if (savedTheme === "contrast") {
    appEl.dataset.theme = "contrast";
  }

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
    };

    const label = map[stateName] || stateName || "Desconocido";
    statusPill.textContent = label;

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
    // historyList.appendChild(item);                       // Para que el mas nuevo este abajo
    historyList.insertBefore(item, historyList.firstChild); // Para que el mas nuevo este arriba

    if (historyList.children.length > 300) {
      historyList.removeChild(historyList.firstElementChild);
    }
    // historyList.scrollTop = historyList.scrollHeight;    // Para que al llegar un dato nuevo el scroll vaya al mas nuevo automaticamentes
  };

  const onCaption = (caption) => {
    if (!caption || !caption.text) {
      return;
    }

    if (caption.source) {
      state.latestSource = caption.source;
      sourceTag.textContent = `source: ${caption.source}`;
    }

    if (caption.is_final) {
      appendHistoryItem(caption);
      liveCaption.textContent = "";
      return;
    }

    liveCaption.textContent = caption.text;
  };

  const loadConfig = async () => {
    try {
      const response = await fetch("/api/config");
      if (!response.ok) return;
      const cfg = await response.json();

      // const url = cfg.ap_url || window.location.origin;
      // const ssid = cfg.ap_ssid ? `Para empezar conectate al WiFi: ${cfg.ap_ssid}` : "WiFi local";
      // networkHint.textContent = `${ssid} | e ingresa en el navegador la URL: ${url}`;
      const url = cfg.ap_url || window.location.origin;
      const ssid = cfg.ap_ssid ? `Para utilizarlo en otro dispositivo recorda conectarte al WiFi: <strong>${cfg.ap_ssid}</strong>` : "WiFi local";
      networkHint.innerHTML = `${ssid}<br>Y abrir en el navegador: <strong>${url}</strong>`;
      sourceTag.textContent = `source: ${cfg.active_source || "-"}`;
    } catch {
      networkHint.textContent = "Modo local";
    }
  };

  const startDemoMode = () => {
    setStatus("idle", "Modo demo local");

    const lines = [
      "Demo local activa.",
      "No hay backend Socket.IO disponible.",
      "Conecta el servidor para subtitulos reales.",
    ];

    let idx = 0;

    setInterval(() => {
      const text = lines[idx % lines.length];
      idx++;

      // partial
      onCaption({
        text,
        is_final: false,
        t_server_ms: Date.now(),
        source: "demo"
      });

      // final después de 1 segundo
      setTimeout(() => {
        onCaption({
          text,
          is_final: true,
          t_server_ms: Date.now(),
          source: "demo"
        });
      }, 1000);

    }, 2500);
  };

  const connectSocket = () => {
    if (typeof io !== "function") {
      startDemoMode();
      return;
    }

    const socket = io({
      reconnection: true,
      reconnectionAttempts: Infinity,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      timeout: 10000,
    });

    socket.on("connect", () => {
      setStatus("idle", "Conectado");
    });

    socket.on("disconnect", () => {
      setStatus("error", "Desconectado, reintentando");
    });

    socket.on("status", (payload) => {
      if (!payload) return;
      setStatus(payload.state, payload.detail);
    });

    socket.on("caption", onCaption);

    socket.on("history", (payload) => {
      clearHistoryUI();
      const items = payload && Array.isArray(payload.items) ? payload.items : [];
      items.forEach((item) => appendHistoryItem(item));
    });

    socket.on("history_cleared", () => {
      clearHistoryUI();
      liveCaption.textContent = "";
    });

    clearBtn.addEventListener("click", async () => {
      socket.emit("clear_history");
      try {
        await fetch("/api/clear", { method: "POST" });
      } catch {
        // Best effort only.
      }
    });
  };

  fontSize.addEventListener("change", () => {
    appEl.dataset.font = fontSize.value;
    localStorage.setItem("incluia_font", fontSize.value);
  });

  contrastToggle.addEventListener("click", () => {
    const nextTheme = appEl.dataset.theme === "contrast" ? "light" : "contrast";
    appEl.dataset.theme = nextTheme;
    localStorage.setItem("incluia_theme", nextTheme);
  });

  clearBtn.addEventListener("click", () => {
    clearHistoryUI();
  });

  menuToggle.addEventListener("click", () => {
    menuToggle.parentElement.classList.toggle("open");
  });

  loadConfig();
  connectSocket();
})();