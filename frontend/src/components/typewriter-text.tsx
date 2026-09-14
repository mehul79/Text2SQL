import { useEffect, useState } from "react";

// The backend sends the final answer as one event, not token-by-token — this
// simulates the reveal client-side rather than claiming real LLM streaming.
export function TypewriterText({ text, className }: { text: string; className?: string }) {
  const [shown, setShown] = useState("");

  useEffect(() => {
    setShown("");
    if (!text) return;

    let i = 0;
    const id = setInterval(() => {
      i++;
      setShown(text.slice(0, i));
      if (i >= text.length) clearInterval(id);
    }, 15);

    return () => clearInterval(id);
  }, [text]);

  return <p className={className}>{shown}</p>;
}
