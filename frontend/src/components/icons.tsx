// Minimal line icons (stroke = currentColor) so nav tint works.
const s = { fill: 'none', stroke: 'currentColor', strokeWidth: 1.8, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const };

export const IconHome = () => (<svg className="nav-ico" viewBox="0 0 24 24" {...s}><path d="M3 11l9-7 9 7"/><path d="M5 10v9h14v-9"/></svg>);
export const IconAssess = () => (<svg className="nav-ico" viewBox="0 0 24 24" {...s}><circle cx="12" cy="12" r="8"/><path d="M12 4v4M12 16v4M4 12h4M16 12h4"/></svg>);
export const IconRank = () => (<svg className="nav-ico" viewBox="0 0 24 24" {...s}><path d="M6 20V10M12 20V4M18 20v-7"/></svg>);
export const IconPlan = () => (<svg className="nav-ico" viewBox="0 0 24 24" {...s}><path d="M5 5h14M5 12h14M5 19h9"/></svg>);
export const IconProfile = () => (<svg className="nav-ico" viewBox="0 0 24 24" {...s}><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 4-6 8-6s8 2 8 6"/></svg>);
export const IconPitches = () => (<svg className="nav-ico" viewBox="0 0 24 24" {...s}><path d="M4 18L5.5 9 9 13 12 7 15 13 18.5 9 20 18Z"/></svg>);

// Unscoped crown glyph (no nav-ico sizing) — used on pitch pins/king cards.
export const Crown = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" {...s}><path d="M4 18L5.5 9 9 13 12 7 15 13 18.5 9 20 18Z"/></svg>
);
