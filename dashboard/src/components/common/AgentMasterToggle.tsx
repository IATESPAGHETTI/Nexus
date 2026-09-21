import { useAgentControl } from "../../context/AgentControlContext";
import styles from "./AgentMasterToggle.module.css";

interface AgentMasterToggleProps {
  compact?: boolean;
}

export function AgentMasterToggle({ compact = false }: AgentMasterToggleProps) {
  const { agentsEnabled, toggleAgents, backendReachable, demoStatus, isLoading } = useAgentControl();

  return (
    <div className={`${styles.container} ${compact ? styles.compact : ""}`}>
      <div className={styles.labelGroup}>
        <span className={styles.label}>NEXUS AGENTS</span>
        <div className={styles.statusBadge}>
          {!agentsEnabled ? (
            <span className={styles.offlineTag}>
              <span className={styles.offlineDot} />
              Agents Offline
            </span>
          ) : isLoading ? (
            <span className={styles.checkingTag}>
              <span className={styles.checkingDot} />
              Probing...
            </span>
          ) : backendReachable ? (
            <span className={styles.onlineTag}>
              <span className={styles.onlineDot} />
              Live Connected ({demoStatus?.agents_reachable_count ?? 0}/{demoStatus?.agents_total ?? 7})
            </span>
          ) : (
            <span className={styles.warningTag}>
              <span className={styles.warningDot} />
              Backend Offline (:8000)
            </span>
          )}
        </div>
      </div>

      <button
        type="button"
        role="switch"
        aria-checked={agentsEnabled}
        className={`${styles.toggleTrack} ${agentsEnabled ? styles.active : ""}`}
        onClick={toggleAgents}
        title={agentsEnabled ? "Switch to Offline/Static Mode" : "Switch to Live Agents API Mode"}
      >
        <span className={`${styles.toggleOption} ${!agentsEnabled ? styles.selected : ""}`}>
          OFF
        </span>
        <span className={`${styles.toggleOption} ${agentsEnabled ? styles.selected : ""}`}>
          ON
        </span>
        <span
          className={`${styles.thumb} ${agentsEnabled ? styles.thumbOn : styles.thumbOff}`}
        />
      </button>
    </div>
  );
}
