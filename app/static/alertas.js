// Notificaciones de escritorio para el semáforo de plazos.
// Sondea /alertas cada 5 minutos; si hay documentos VENCIDO/POR_VENCER
// no mostrados antes en este navegador, dispara una notificación nativa
// (queda en el Centro de Actividades de Windows aunque cierre el toast).

const ALERTAS_POLL_MS = 5 * 60 * 1000; // 5 minutos
const ALERTAS_STORAGE_KEY = "sgd_alertas_mostradas";

function alertasYaMostradas() {
  try {
    const raw = localStorage.getItem(ALERTAS_STORAGE_KEY);
    return raw ? new Set(JSON.parse(raw)) : new Set();
  } catch {
    return new Set();
  }
}

function guardarAlertasMostradas(set) {
  try {
    localStorage.setItem(ALERTAS_STORAGE_KEY, JSON.stringify([...set]));
  } catch {
    // localStorage no disponible (modo privado, etc.) - no es critico.
  }
}

function etiquetaEstado(estado) {
  return estado === "VENCIDO" ? "Vencido" : "Por vencer";
}

async function revisarAlertas() {
  let alertas;
  try {
    const resp = await fetch("/alertas", { credentials: "same-origin" });
    if (!resp.ok) return; // tolerante a fallos: no rompe el panel
    alertas = await resp.json();
  } catch {
    return; // red caida, servidor abajo, etc.
  }

  const mostradas = alertasYaMostradas();
  let huboNuevas = false;

  for (const doc of alertas) {
    const clave = `${doc.id}:${doc.estado}`;
    if (mostradas.has(clave)) continue;

    new Notification(`SGD-SINOLE — ${etiquetaEstado(doc.estado)}`, {
      body: doc.n_documento,
      tag: clave,
    });
    mostradas.add(clave);
    huboNuevas = true;
  }

  if (huboNuevas) guardarAlertasMostradas(mostradas);
}

function actualizarBotonAlertas(boton, mensaje) {
  if (!("Notification" in window)) {
    boton.textContent = "Notificaciones no soportadas";
    boton.disabled = true;
    return;
  }
  if (Notification.permission === "granted") {
    boton.textContent = "Alertas activadas";
    boton.classList.remove("btn-warning");
    boton.classList.add("btn-outline-secondary");
    boton.disabled = true;
    mensaje.classList.add("d-none");
    revisarAlertas();
    setInterval(revisarAlertas, ALERTAS_POLL_MS);
  } else if (Notification.permission === "denied") {
    boton.textContent = "Alertas bloqueadas";
    boton.classList.remove("btn-warning");
    boton.classList.add("btn-outline-secondary");
    boton.disabled = true;
    mensaje.textContent = "Bloqueaste las notificaciones para este sitio. Para activarlas: click en el candado junto a la URL del navegador > Notificaciones > Permitir, y recarga la página.";
    mensaje.classList.remove("d-none");
  } else {
    boton.textContent = "Activar alertas";
    boton.disabled = false;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const boton = document.getElementById("btn-activar-alertas");
  const mensaje = document.getElementById("alertas-mensaje");
  if (!boton || !mensaje) return;

  actualizarBotonAlertas(boton, mensaje);

  boton.addEventListener("click", async () => {
    if (!("Notification" in window)) return;
    await Notification.requestPermission();
    actualizarBotonAlertas(boton, mensaje);
  });
});
