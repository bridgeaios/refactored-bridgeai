/** WebSocket server: push contract events to subscribed clients. */
import { WebSocketServer } from "ws";
import { pollEvents } from "../services/contractWatcher.js";
import config from "../config.js";

const clients = new Set();

export function attachWebSocket(server) {
  const wss = new WebSocketServer({ noServer: true });

  server.on("upgrade", (req, socket, head) => {
    const url = new URL(req.url || "/", `http://${req.headers.host}`);
    if (url.pathname === "/ws/events") {
      wss.handleUpgrade(req, socket, head, (ws) => {
        wss.emit("connection", ws, req);
      });
    } else {
      socket.destroy();
    }
  });

  wss.on("connection", (ws) => {
    clients.add(ws);
    ws.send(JSON.stringify({ type: "connected", ts: Date.now() }));
    ws.on("close", () => clients.delete(ws));
    ws.on("error", () => clients.delete(ws));
  });

  if (config.contractAddress) {
    (async () => {
      for await (const event of pollEvents()) {
        const msg = JSON.stringify({ type: "contract_event", event });
        for (const c of clients) {
          if (c.readyState === 1) c.send(msg);
        }
      }
    })().catch((e) => console.error("[ws/events]", e));
  }

  return wss;
}
