import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { useMotionValueEvent, useReducedMotion, useScroll } from "motion/react";
import { useAgentControl } from "../../context/AgentControlContext";
import { useActiveIncident } from "../../api/useActiveIncident";
import { PIPELINE_AGENTS } from "../../lib/presentation";
import styles from "./Hero.module.css";

const TITLE = "The investigation layer for production failures".split(" ");
const clamp01 = (v: number) => Math.min(1, Math.max(0, v));

// The frame's inner UI is designed at a fixed size and scaled to the frame's
// current width, so it stays legible while the frame grows on scroll.
const DESIGN_W = 900;
const DESIGN_H = 506;

function FrameContents() {
  // Real state only. Agents OFF / probing / unreachable read as exactly that.
  const { agentsEnabled, backendReachable, demoStatus, isLoading } = useAgentControl();
  const { model } = useActiveIncident();
  const live = agentsEnabled && backendReachable;
  const online = demoStatus?.agents_reachable_count ?? 0;
  const total = demoStatus?.agents_total ?? 7;
  const state = !agentsEnabled ? "AGENTS OFFLINE" : isLoading ? "CONNECTING…" : !backendReachable ? "BACKEND UNREACHABLE" : "LIVE";

  return (
    <>
      <div className={styles.frameBar}>
        <span className={styles.dots}>
          <i /> <i /> <i />
        </span>
        <span className={styles.frameTitle}>nexus · system status</span>
        <span className={`${styles.frameState} ${live ? styles.frameLive : ""}`}>{state}</span>
      </div>
      <div className={styles.frameBody}>
        <div className={styles.tiles}>
          <div className={styles.tile}>
            <span className={styles.tileLabel}>Agents</span>
            <span className={styles.tileValue}>{!agentsEnabled ? "Offline" : live ? `${online} of ${total}` : "Unknown"}</span>
            <span className={styles.tileSub}>{live ? "live probe of each service" : "not being read"}</span>
          </div>
          <div className={styles.tile}>
            <span className={styles.tileLabel}>Simulated service</span>
            <span className={styles.tileValue}>
              {!agentsEnabled ? "Not checked" : live ? (demoStatus?.production_reachable ? "Reachable" : "Unreachable") : "Unknown"}
            </span>
            <span className={styles.tileSub}>the order service NEXUS investigates</span>
          </div>
          <div className={styles.tile}>
            <span className={styles.tileLabel}>Active incident</span>
            <span className={styles.tileValue}>{model ? model.status.charAt(0) + model.status.slice(1).toLowerCase() : "None"}</span>
            <span className={styles.tileSub}>{model ? model.description : live ? "none recorded yet" : "requires a live backend"}</span>
          </div>
          <div className={styles.tile}>
            <span className={styles.tileLabel}>Recovery</span>
            <span className={styles.tileValue}>Needs approval</span>
            <span className={styles.tileSub}>by design, enforced by guardrails</span>
          </div>
        </div>

        <ul className={styles.agentList}>
          {PIPELINE_AGENTS.map((a) => {
            const st = live ? model?.pipeline[a.key].status : undefined;
            const cls = st === "working" ? styles.aWorking : st === "reported" ? styles.aDone : st === "failed" ? styles.aFailed : "";
            return (
              <li key={a.key} className={`${styles.agentRow} ${cls}`}>
                <span className={styles.agentDot} />
                <span className={styles.agentName}>{a.name}</span>
                <span className={styles.agentState}>{st && st !== "idle" ? st : live ? "idle" : "—"}</span>
              </li>
            );
          })}
        </ul>
      </div>
      {!live && <div className={styles.frameNote}>Nothing here is simulated. With agents OFF this frame stays empty on purpose.</div>}
    </>
  );
}

interface HeroPinnedProps {
  onDemoClick: () => void;
}

export function HeroPinned({ onDemoClick }: HeroPinnedProps) {
  const wrapRef = useRef<HTMLElement>(null);
  const stickyRef = useRef<HTMLDivElement>(null);
  const frameRef = useRef<HTMLDivElement>(null);
  const prefersReduced = useReducedMotion();
  const [narrow, setNarrow] = useState(false);
  const [ready, setReady] = useState(false);
  const noMotion = Boolean(prefersReduced) || narrow;

  useEffect(() => {
    const mq = window.matchMedia("(max-width: 760px), (max-height: 560px)");
    const on = () => setNarrow(mq.matches);
    on();
    mq.addEventListener("change", on);
    setReady(true);
    return () => mq.removeEventListener("change", on);
  }, []);

  const { scrollYProgress } = useScroll({ target: wrapRef, offset: ["start start", "end end"] });
  useMotionValueEvent(scrollYProgress, "change", (p) => {
    const el = stickyRef.current;
    if (!el || noMotion) return;
    el.style.setProperty("--grow-progress", String(clamp01((p - 0.06) / 0.6)));
    el.style.setProperty("--intro-progress", String(clamp01((p - 0.6) / 0.28)));
  });

  // Scale the fixed-size frame UI to the frame's live width.
  useLayoutEffect(() => {
    const frame = frameRef.current;
    if (!frame) return;
    const apply = () => frame.style.setProperty("--s", String(frame.getBoundingClientRect().width / DESIGN_W));
    apply(); // synchronous first pass, so the first paint is already scaled correctly
    const ro = new ResizeObserver(apply);
    ro.observe(frame);
    window.addEventListener("resize", apply);
    return () => {
      ro.disconnect();
      window.removeEventListener("resize", apply);
    };
  }, [narrow]);

  return (
    <section ref={wrapRef} className={`${styles.wrap} ${noMotion ? styles.noMotion : ""}`}>
      <div ref={stickyRef} className={`${styles.sticky} ${ready ? styles.ready : ""}`}>
        <div className={styles.perspective} aria-hidden="true" />

        <div className={styles.copyZone}>
          <div className={styles.heroCopy}>
            <h1 className={styles.title}>
              {TITLE.map((w, i) => (
                <span key={i} className={styles.word} style={{ animationDelay: `${i * 0.07}s` }}>
                  {w}
                </span>
              ))}
            </h1>
            <p className={styles.desc}>
              NEXUS detects production failures, investigates them with real system evidence, challenges its own
              diagnosis, and recovers the system with human approval.
            </p>
            <button type="button" className={styles.cta} onClick={onDemoClick}>
              Run the demo →
            </button>
          </div>

          <div className={styles.introCopy}>
            <p className={styles.overline}>Human in the loop</p>
            <h2 className={styles.introTitle}>Nothing runs without approval</h2>
            <p className={styles.introDesc}>
              An agent proposes a bounded recovery, guardrails validate it, and it executes only after a person says yes.
            </p>
          </div>
        </div>

        <div ref={frameRef} className={styles.frame}>
          <div className={styles.frameInner} style={{ width: DESIGN_W, height: DESIGN_H }}>
            <FrameContents />
          </div>
        </div>
      </div>
    </section>
  );
}
