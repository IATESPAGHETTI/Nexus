import type { CSSProperties, PropsWithChildren } from "react";
import styles from "./GlassSurface.module.css";

interface GlassSurfaceProps {
  as?: "div" | "section" | "article";
  elevation?: "panel" | "raised";
  /** Denser material — nav/topbar/utility chrome. */
  strong?: boolean;
  /** Lightest material — floating status/utility cards. */
  light?: boolean;
  /** Adds a subtle hover lift; use when the surface wraps a click target. */
  interactive?: boolean;
  className?: string;
  style?: CSSProperties;
}

/**
 * The base "layered physical material" surface used throughout NEXUS:
 * translucent + blurred, with soft directional shadow instead of any glow
 * or colored border. Never fully transparent — it should read as a solid
 * panel that light passes through. Three densities (default/`strong`/
 * `light`) give the background -> glass shell -> panels -> floating
 * elements depth the visual design calls for.
 */
export function GlassSurface({
  as = "div",
  elevation = "panel",
  strong = false,
  light = false,
  interactive = false,
  className,
  style,
  children,
}: PropsWithChildren<GlassSurfaceProps>) {
  const Tag = as;
  const classes = [
    styles.surface,
    elevation === "raised" ? styles.raised : styles.panel,
    strong ? styles.strong : "",
    light ? styles.light : "",
    interactive ? styles.interactive : "",
    className ?? "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <Tag className={classes} style={style}>
      {children}
    </Tag>
  );
}
