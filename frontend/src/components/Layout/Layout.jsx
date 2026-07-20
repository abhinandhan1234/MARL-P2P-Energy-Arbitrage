import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import TopBar from "./TopBar";
import { useWebSocket } from "../../api/useWebSocket";
export default function Layout() { useWebSocket(); return <div className="app-shell"><Sidebar /><main><TopBar /><Outlet /></main></div>; }
