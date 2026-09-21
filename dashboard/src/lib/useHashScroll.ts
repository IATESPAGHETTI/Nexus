import { useEffect } from "react";
import { useLocation } from "react-router-dom";

/** Smooth-scrolls to `#id` whenever the URL hash changes (react-router does not). */
export function useHashScroll() {
  const { hash, pathname } = useLocation();
  useEffect(() => {
    if (!hash) return;
    const t = window.setTimeout(() => {
      document.getElementById(hash.slice(1))?.scrollIntoView({ behavior: "smooth" });
    }, 60);
    return () => window.clearTimeout(t);
  }, [hash, pathname]);
}
