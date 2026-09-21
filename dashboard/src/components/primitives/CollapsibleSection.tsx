import { useState, type PropsWithChildren } from "react";
import { motion, AnimatePresence } from "motion/react";
import { GlassSurface } from "./GlassSurface";
import styles from "./CollapsibleSection.module.css";

interface CollapsibleSectionProps {
  title: string;
  meta?: string;
  /** One-sentence "professor mode" explanation of what this panel is,
   * shown as a native tooltip on the title — not a tutorial overlay. */
  hint?: string;
  defaultOpen?: boolean;
}

export function CollapsibleSection({
  title,
  meta,
  hint,
  defaultOpen = false,
  children,
}: PropsWithChildren<CollapsibleSectionProps>) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <GlassSurface>
      <button
        className={styles.header}
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        title={hint}
      >
        <span className={styles.title}>{title}</span>
        <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {meta && <span className={styles.meta}>{meta}</span>}
          <span className={`${styles.chevron} ${open ? styles.open : ""}`}>&#9656;</span>
        </span>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            className={styles.body}
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ type: "spring", stiffness: 300, damping: 32 }}
          >
            <div className={styles.bodyInner}>{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </GlassSurface>
  );
}
