import { useGridState } from "../api/useGridState";
import { useStore } from "../store/useStore";
export function useLiveData() { const grid = useGridState(); const live = useStore((s) => s.liveAgentData); return { data: live || grid.data, isLoading: !live && grid.isLoading, error: grid.error }; }
