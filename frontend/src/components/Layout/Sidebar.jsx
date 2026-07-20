import { BarChart3, Blocks, BrainCircuit, LayoutDashboard, Network } from "lucide-react";
import { NavLink } from "react-router-dom";
const links = [["/dashboard", "Command center", LayoutDashboard], ["/marketplace", "Marketplace", BarChart3], ["/ai-predictions", "AI forecasts", BrainCircuit], ["/blockchain", "Settlement", Blocks], ["/smart-grid", "Grid topology", Network]];
export default function Sidebar() { return <aside className="sidebar"><NavLink className="brand" to="/dashboard">SOLAR<span>X</span><small>ENERGY EXCHANGE</small></NavLink><nav>{links.map(([to, label, Icon]) => <NavLink key={to} to={to}><Icon size={18}/>{label}</NavLink>)}</nav><div className="sidebar-foot"><i/> 21 agents online</div></aside>; }
