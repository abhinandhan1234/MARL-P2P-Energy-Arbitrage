import { useStatus } from "../../api/useGridState";
import { useLiveData } from "../../hooks/useLiveData";
const Metric = ({label, value, unit}) => <article className="metric"><span>{label}</span><strong>{value}</strong><small>{unit}</small></article>;
export default function MetricsSummary() { const { data } = useLiveData(); const { data: status } = useStatus(); return <div className="metrics"><Metric label="Clearing price" value={data?.clearing_price?.toFixed(2) ?? "--"} unit="Rs / kWh"/><Metric label="P2P volume" value={data?.total_p2p_volume_kwh?.toFixed(1) ?? "--"} unit="kWh"/><Metric label="Grid import" value={data?.grid_import_kw?.toFixed(1) ?? "--"} unit="kW"/><Metric label="Best reward" value={status?.best_reward?.toFixed?.(2) ?? "--"} unit={status?.state || "IDLE"}/></div>; }
