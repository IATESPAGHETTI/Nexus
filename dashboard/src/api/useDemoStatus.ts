import { useQuery } from "@tanstack/react-query";
import { getDemoStatus } from "./client";

const STATUS_POLL_MS = 5000;

/** Real system-status probe (backend/app/demo.py) — production reachability
 * and A2A agent-card reachability, polled every 5s. Never a hardcoded
 * "online"; a probe that fails just reports false. */
export function useDemoStatus() {
  return useQuery({
    queryKey: ["demo-status"],
    queryFn: getDemoStatus,
    refetchInterval: STATUS_POLL_MS,
    refetchIntervalInBackground: true,
    retry: 0,
  });
}
