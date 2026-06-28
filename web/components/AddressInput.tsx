"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

const COOKIE_NAME = "lastAddress";
// 1 year — long enough that returning users don't lose their last search.
const COOKIE_MAX_AGE = 60 * 60 * 24 * 365;

type Hit = {
  lat: number;
  lng: number;
  display_name: string;
};

/**
 * Address bar for /play with debounced typeahead against /api/geocode.
 *
 * - Pauses 280 ms after the user stops typing before hitting the API (Nominatim's
 *   1 req/sec policy + nice UX).
 * - Aborts in-flight requests when the input changes (no stale results).
 * - Submitting (Enter or button) navigates to /play?q=<value>.
 * - Clicking a suggestion does the same, prefilling the input.
 */
export function AddressInput({ defaultValue = "" }: { defaultValue?: string }) {
  const router = useRouter();
  const [value, setValue] = useState(defaultValue);
  const [hits, setHits] = useState<Hit[]>([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const abortRef = useRef<AbortController | null>(null);
  const timerRef = useRef<number | null>(null);

  // Remember successful searches so a returning visitor lands on their last
  // neighborhood instead of an empty map. Server reads this cookie in /play.
  useEffect(() => {
    if (defaultValue) {
      document.cookie =
        `${COOKIE_NAME}=${encodeURIComponent(defaultValue)}; ` +
        `path=/; max-age=${COOKIE_MAX_AGE}; SameSite=Lax`;
    }
  }, [defaultValue]);

  // Debounced suggestion fetch.
  useEffect(() => {
    const q = value.trim();
    if (q.length < 3 || q === defaultValue.trim()) {
      setHits([]);
      return;
    }
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = window.setTimeout(async () => {
      abortRef.current?.abort();
      const ctrl = new AbortController();
      abortRef.current = ctrl;
      try {
        const r = await fetch(
          `/api/geocode?q=${encodeURIComponent(q)}&limit=6`,
          { signal: ctrl.signal },
        );
        if (!r.ok) {
          setHits([]);
          return;
        }
        const data = (await r.json()) as Hit[];
        setHits(Array.isArray(data) ? data : []);
        setActive(-1);
      } catch {
        // aborted or network error — leave hits as-is to avoid flicker
      }
    }, 280);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [value, defaultValue]);

  const submit = (q: string) => {
    setOpen(false);
    setValue(q);
    router.push(`/play?q=${encodeURIComponent(q)}`);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!open || hits.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((i) => Math.min(i + 1, hits.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((i) => Math.max(i - 1, -1));
    } else if (e.key === "Enter" && active >= 0) {
      e.preventDefault();
      submit(hits[active].display_name);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  };

  const showSuggestions = open && hits.length > 0;

  return (
    <form
      action="/play"
      method="get"
      className="play-form"
      onSubmit={(e) => {
        e.preventDefault();
        submit(value);
      }}
    >
      <div className="play-input-wrap">
        <svg
          className="play-search-icon"
          aria-hidden="true"
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <circle cx="11" cy="11" r="7" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
        <input
          type="text"
          name="q"
          value={value}
          onChange={(e) => {
            setValue(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => {
            setTimeout(() => setOpen(false), 150);
          }}
          onKeyDown={handleKeyDown}
          placeholder="Your Amsterdam address"
          autoComplete="off"
          autoCorrect="off"
          spellCheck={false}
          required
          minLength={3}
          className="play-input"
          aria-autocomplete="list"
          aria-expanded={showSuggestions}
        />
        {value && (
          <button
            type="button"
            className="play-clear"
            aria-label="Clear"
            onMouseDown={(e) => {
              e.preventDefault();
              setValue("");
              setHits([]);
              setOpen(false);
            }}
          >
            ×
          </button>
        )}
        {showSuggestions && (
          <ul className="play-suggestions" role="listbox">
            {hits.map((h, i) => (
              <li key={`${h.lat},${h.lng}`}>
                <button
                  type="button"
                  className={`play-suggestion ${i === active ? "active" : ""}`}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    submit(h.display_name);
                  }}
                  onMouseEnter={() => setActive(i)}
                >
                  {h.display_name}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </form>
  );
}
