import { useEffect, useRef } from "react";

/** Executa `onIdle` após `seconds` sem interação. Reinicia a cada toque/tecla. */
export function useIdleReset(seconds: number | null, onIdle: () => void) {
  const cb = useRef(onIdle);
  cb.current = onIdle;

  useEffect(() => {
    if (!seconds) return;
    let t: number;
    const arm = () => {
      window.clearTimeout(t);
      t = window.setTimeout(() => cb.current(), seconds * 1000);
    };
    const evts = ["pointerdown", "keydown", "touchstart"] as const;
    evts.forEach((e) => window.addEventListener(e, arm, { passive: true }));
    arm();
    return () => {
      window.clearTimeout(t);
      evts.forEach((e) => window.removeEventListener(e, arm));
    };
  }, [seconds]);
}
