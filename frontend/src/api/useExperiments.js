import { useQuery } from "@tanstack/react-query";
import { api } from "./client";
export const useExperiments = () => useQuery({ queryKey: ["experiments"], queryFn: () => api.get("/api/experiments").then((r) => r.data), refetchInterval: 5000 });
