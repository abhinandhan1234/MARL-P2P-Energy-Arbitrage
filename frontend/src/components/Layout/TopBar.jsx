import { useStore } from "../../store/useStore";
export default function TopBar() { const status = useStore((s) => s.connectionStatus); return <header className="topbar"><span>LIVE MARKET / KLS VDIT CAMPUS</span><div className="live-pill"><i/> {status}</div></header>; }
