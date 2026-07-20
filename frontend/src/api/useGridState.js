import { useQuery } from "@tanstack/react-query";
import { api } from "./client";
export const useGridState = () => useQuery({ queryKey: ["grid-state"], queryFn: () => api.get("/api/grid/state").then((r) => r.data), refetchInterval: 5000 });
export const useStatus = () => useQuery({ queryKey: ["status"], queryFn: () => api.get("/api/status").then((r) => r.data), refetchInterval: 5000 });
