// Phone-sized screens: the sidebar becomes a drawer and the big type steps down. One breakpoint,
// read live, so rotating a phone or resizing a window re-lays the page.
import { useEffect, useState } from "react";

const QUERY = "(max-width: 767px)";

export function useNarrow(): boolean {
  const [narrow, setNarrow] = useState(() => typeof window !== "undefined" && window.matchMedia(QUERY).matches);
  useEffect(() => {
    const media = window.matchMedia(QUERY);
    const update = () => setNarrow(media.matches);
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);
  return narrow;
}
