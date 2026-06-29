"use client";

import { useEffect, useState } from "react";

/**
 * Admin / dev configuration overlay for /play. Three sliders to tune render
 * behavior at runtime. Closed by default; state persists in localStorage so
 * a tester's last settings survive a refresh.
 *
 * This is an admin-only tool — will get hidden behind an env / feature flag
 * before public launch.
 */

export type AdminSettings = {
  /** Cap on tree markers per viewport. Forwarded as max_pins to /api/trees. */
  treeCap: number;
  /** Number of creature sprites animating on the map. Overrides the
   *  viewport-area heuristic in PlayMap when set. */
  creatureSlots: number;
  /** Creature flight speed in meters/second. Overrides PlayMap's SPEED_MPS. */
  creatureSpeedMps: number;
};

export const ADMIN_DEFAULTS: AdminSettings = {
  treeCap: 100,
  creatureSlots: 8,
  creatureSpeedMps: 6,
};

// Hard caps that have been verified not to break the renderer. The user
// confirmed 500 markers is OK; the others are conservative.
const LIMITS = {
  treeCap:          { min: 20, max: 500, step: 10 },
  creatureSlots:    { min:  0, max:  40, step:  1 },
  creatureSpeedMps: { min:  1, max:  30, step:  1 },
};

const LS_KEY = "creatures-ams.admin";

function loadFromLocalStorage(): AdminSettings {
  if (typeof window === "undefined") return ADMIN_DEFAULTS;
  try {
    const raw = window.localStorage.getItem(LS_KEY);
    if (!raw) return ADMIN_DEFAULTS;
    const parsed = JSON.parse(raw);
    return {
      treeCap:
        typeof parsed.treeCap === "number"
          ? clamp(parsed.treeCap, LIMITS.treeCap.min, LIMITS.treeCap.max)
          : ADMIN_DEFAULTS.treeCap,
      creatureSlots:
        typeof parsed.creatureSlots === "number"
          ? clamp(parsed.creatureSlots, LIMITS.creatureSlots.min, LIMITS.creatureSlots.max)
          : ADMIN_DEFAULTS.creatureSlots,
      creatureSpeedMps:
        typeof parsed.creatureSpeedMps === "number"
          ? clamp(parsed.creatureSpeedMps, LIMITS.creatureSpeedMps.min, LIMITS.creatureSpeedMps.max)
          : ADMIN_DEFAULTS.creatureSpeedMps,
    };
  } catch {
    return ADMIN_DEFAULTS;
  }
}

function clamp(n: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, n));
}

export function AdminPanel({
  settings,
  onChange,
}: {
  settings: AdminSettings;
  onChange: (next: AdminSettings) => void;
}) {
  const [open, setOpen] = useState(false);

  const set = <K extends keyof AdminSettings>(key: K, value: number) => {
    const next = { ...settings, [key]: value };
    onChange(next);
    try {
      window.localStorage.setItem(LS_KEY, JSON.stringify(next));
    } catch {
      /* localStorage unavailable — settings just won't persist */
    }
  };

  if (!open) {
    return (
      <button
        type="button"
        className="admin-collapsed-handle"
        aria-label="Show admin controls"
        title="Admin"
        onClick={() => setOpen(true)}
      >
        <svg
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
          <circle cx="12" cy="12" r="3" />
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h0a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51h0a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v0a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
        </svg>
      </button>
    );
  }

  return (
    <aside className="admin-panel">
      <div className="admin-panel-head">
        <span className="admin-panel-title">Admin</span>
        <button
          type="button"
          className="admin-panel-close"
          aria-label="Hide admin controls"
          onClick={() => setOpen(false)}
        >
          ×
        </button>
      </div>
      <div className="admin-panel-body">
        <SliderRow
          label="Tree markers"
          value={settings.treeCap}
          limits={LIMITS.treeCap}
          onChange={(v) => set("treeCap", v)}
        />
        <SliderRow
          label="Animals on screen"
          value={settings.creatureSlots}
          limits={LIMITS.creatureSlots}
          onChange={(v) => set("creatureSlots", v)}
        />
        <SliderRow
          label="Animal speed (m/s)"
          value={settings.creatureSpeedMps}
          limits={LIMITS.creatureSpeedMps}
          onChange={(v) => set("creatureSpeedMps", v)}
        />
      </div>
    </aside>
  );
}

function SliderRow({
  label,
  value,
  limits,
  onChange,
}: {
  label: string;
  value: number;
  limits: { min: number; max: number; step: number };
  onChange: (v: number) => void;
}) {
  return (
    <div className="admin-slider-row">
      <div className="admin-slider-head">
        <span className="admin-slider-label">{label}</span>
        <span className="admin-slider-value">{value}</span>
      </div>
      <input
        type="range"
        min={limits.min}
        max={limits.max}
        step={limits.step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="admin-slider"
      />
    </div>
  );
}

/** Hydrate the admin settings from localStorage on the client. Returns
 *  the persisted settings on first render after mount; defaults before. */
export function useAdminSettings(): [AdminSettings, (s: AdminSettings) => void] {
  const [settings, setSettings] = useState<AdminSettings>(ADMIN_DEFAULTS);
  useEffect(() => {
    setSettings(loadFromLocalStorage());
  }, []);
  return [settings, setSettings];
}
