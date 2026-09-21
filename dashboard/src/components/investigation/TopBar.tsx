import { Link } from "react-router-dom";
import { GlassSurface } from "../primitives/GlassSurface";
import { MonoLabel } from "../primitives/MonoLabel";
import { PhaseTimeline } from "./PhaseTimeline";
import styles from "./TopBar.module.css";

interface TopBarProps {
  incidentId: string;
  description: string;
  phaseIndex: number;
}

export function TopBar({ incidentId, description, phaseIndex }: TopBarProps) {
  return (
    <GlassSurface strong elevation="raised" className={styles.bar}>
      <div className={styles.identity}>
        <Link to="/" className={styles.back}>
          &larr; NEXUS
        </Link>
        <div className={styles.desc} title={description}>
          {description}
        </div>
        <div className={styles.id}>
          <MonoLabel>{incidentId}</MonoLabel>
        </div>
      </div>
      <PhaseTimeline currentIndex={phaseIndex} />
    </GlassSurface>
  );
}
