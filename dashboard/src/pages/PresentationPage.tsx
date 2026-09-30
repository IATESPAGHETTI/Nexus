import { useHashScroll } from "../lib/useHashScroll";
import { HeroPinned } from "../components/story/HeroPinned";
import {
  FinalCta,
  PillarsNav,
  ProblemSection,
  StatementReveal,
  StepsRail,
  TechMarquee,
} from "../components/story/StorySections";
import { SolutionCompare } from "../components/story/SolutionCompare";
import { AgentBento } from "../components/story/AgentBento";
import { ArchitectureSection } from "../components/story/ArchitectureSection";
import { LiveBand } from "../components/story/LiveBand";
import styles from "../components/story/Story.module.css";

const goLive = () => document.getElementById("pl-live")?.scrollIntoView({ behavior: "smooth" });

export function PresentationPage() {
  useHashScroll();
  return (
    <div className={styles.page}>
      <HeroPinned onDemoClick={goLive} />
      <TechMarquee />
      <ProblemSection />
      <StatementReveal />
      <SolutionCompare />
      <AgentBento />
      <ArchitectureSection />
      <StepsRail />
      <LiveBand />
      <FinalCta onClick={goLive} />
      <PillarsNav />
    </div>
  );
}
