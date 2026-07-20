import { useEffect } from "react";
import { useStore } from "../store/useStore";

export function useWebSocket() {
  const ingest = useStore((s) => s.ingestLiveData); const setStatus = useStore((s) => s.setConnectionStatus);
  useEffect(() => {
    let socket; let retry = 1000; let closed = false; let timer;
    const connect = () => {
      const base = import.meta.env.VITE_WS_URL || `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/live`;
      socket = new WebSocket(base);
      socket.onopen = () => { retry = 1000; setStatus("live"); };
      socket.onmessage = ({ data }) => { try { ingest(JSON.parse(data)); } catch { /* malformed messages are ignored */ } };
      socket.onclose = () => { if (!closed) { setStatus("reconnecting"); timer = setTimeout(connect, retry); retry = Math.min(retry * 2, 30000); } };
      socket.onerror = () => socket.close();
    }; connect();
    return () => { closed = true; clearTimeout(timer); socket?.close(); };
  }, [ingest, setStatus]);
}
