# Hostel Mess Menu Optimizer — Design System (Apple-inspired)

*Guided by the `apple-design` skill: fluidity, direct manipulation, restraint, and craft. Adapted for Streamlit + Plotly.*

## 1) Goals
- Make tradeoffs between cost, nutrition, and satisfaction feel obvious and tangible
- Keep the flow frictionless: pick a point on Pareto front → see full weekly menu instantly
- Prioritize clarity over decoration; every element earns its place
- Respect accessibility (reduced motion, reduced transparency/contrast)
- Feel calm and confident, not playful for the sake of it

## 2) Design Principles (mapped)
| Principle | Application in this app |
|---|---|
| Response (kill latency) | Show loading states immediately, use cached results, update charts on interaction without reload flicker |
| Direct manipulation | Let user drag/slide the "tradeoff" control; Pareto scatter points should feel selectable with instant feedback |
| Interruptibility | Don't block UI during generation; allow re-generating with different seeds/params without locking controls |
| Springs over tweens | For any in-app animated transitions (if custom CSS/JS), use spring-like easing; in Streamlit prefer snappy CSS transitions with `ease-out` (100-200ms) |
| Spatial consistency | Menu table opens from context of selected solution; filters stay in place; navigation is predictable |
| Restraint | One primary action per view (e.g. "Generate Menus"); secondary actions grouped, advanced in expander |
| Hierarchy & clarity | Most important: Pareto front + chosen menu. Supporting: objectives breakdown, violations, export |

## 3) Typography
Use system fonts first for legibility and performance.

```css
:root {
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  --text-primary: rgba(0,0,0,0.9);
  --text-secondary: rgba(0,0,0,0.6);
  line-height: 1.5;
}
```

- Headings: tighter leading (1.05-1.15), slightly negative tracking for large sizes
- Body: ~1.5 line-height, tracking near 0
- Use rem/em for spacing so it scales with user text settings
- Prefer weight over size to emphasize

## 4) Color & Materials
Keep surfaces clean. Use subtle translucency only where it adds hierarchy (headers/toolbars). Avoid stacking translucent layers.

| Token | Purpose | Value (light) |
|---|---|---|
| `--bg` | App background | `#f5f5f7` (soft off-white, like Apple system grouped bg) |
| `--surface` | Cards/tables | `#ffffff` |
| `--surface-translucent` | Sticky header/toolbar (if used) | `rgba(255,255,255,0.72)` with `backdrop-filter: saturate(180%) blur(20px)` |
| `--border` | Dividers | `rgba(0,0,0,0.08)` |
| `--text-primary` | Primary text | `rgba(0,0,0,0.9)` |
| `--text-secondary` | Labels/metadata | `rgba(0,0,0,0.6)` |
| `--accent` | Primary actions/selected point | `#007AFF` (system blue) |
| `--success/warn/error` | Status | system colors as appropriate |
| `--scrim` | Modal focus (if any) | `rgba(0,0,0,0.4)` |

For dark mode (optional), mirror with system colors. If adding custom CSS in Streamlit, gate with `prefers-color-scheme`.

## 5) Spacing, Radius, Elevation
Consistent rhythm is craft.

- Base unit: 4px. Scale: 4,8,12,16,20,24,32,48,...
- Border radius: 8px (controls), 12px (cards), 16px (panels)
- Shadows: subtle, context-aware
  - Cards: `0 1px 2px rgba(0,0,0,0.02), 0 4px 12px rgba(0,0,0,0.04)`
  - Elevated (dropdowns): `0 4px 16px rgba(0,0,0,0.08)`
- Borders: hairline `1px solid rgba(0,0,0,0.06)`

## 6) Motion
Keep motion purposeful and interruptible. In Streamlit we have limited control, but follow these rules:

| Interaction | Motion | Notes |
|---|---|---|
| Button press | Instant feedback on active/hover | Use CSS `:active { transform: scale(0.98); } transition: transform 100ms ease-out;` |
| Plot/selection changes | Snappy, no long fades | Avoid multi-second animations; prefer instant update |
| Expander open/close | Subtle | Keep native Streamlit feel; don't override heavily |
| Page transitions | None or minimal | Restraint |

- Default easing: `cubic-bezier(0.25, 0.1, 0.25, 1)` or just `ease-out` for entrances
- Durations: 100-200ms for micro-interactions, max ~300ms
- **Reduced motion**: respect `prefers-reduced-motion: reduce` - disable transforms/animations, use instant state changes or opacity cross-fades only

## 7) Layout & Information Architecture
Structure around the decision flow:

1. **Sidebar / Controls** (left): Data sources, NSGA-II params (pop size, generations), seeds, constraints toggles, "Generate" CTA
2. **Main - Pareto Explorer**: Scatter plot (f1 cost vs f2 nutrition dev, color/size by f3 dissatisfaction). Clear axes labels with units. Selected point highlighted.
3. **Tradeoff Control**: Slider/selector to pick balance along front (or click point). Shows objective values for selected.
4. **Weekly Menu**: Clean table grouped by Day/Meal with Dish, Veg/Non-veg, Cost, Kcal, Protein, Rating. Subtle row states.
5. **Comparison**: vs Current Menu, Random Valid, Greedy Cheapest - side-by-side metrics
6. **Export**: Excel/PDF buttons, unobtrusive

Keep related items grouped by proximity. Use cards/containers to create hierarchy without heavy dividers.

## 8) Components (Streamlit adaptations)
| Component | Guidance |
|---|---|
| `st.button` | Primary style via custom CSS (blue, subtle scale on press). Destructive rare. |
| `st.slider` | For tradeoff selection; label clearly with current values |
| `st.dataframe` / `st.table` | Clean, readable. Align numbers right, text left. Add subtle hover. |
| `st.plotly_chart` | Custom colors, clean grid, no chartjunk. Highlight selected point with larger marker + ring. |
| `st.expander` | For advanced params/notes. Keep collapsed by default. |
| `st.metric` | For key objectives (cost/day, kcal deviation, rating) with deltas vs baseline |
| `st.tabs` | For "Pareto", "Menu", "Comparison", "Export" to reduce scroll |

## 9) Interaction Details
- **Selection**: Clicking a Pareto point updates the entire menu view instantly (direct manipulation)
- **Feedback**: Button shows active state immediately; charts update without spinner flicker where possible
- **Hysteresis**: N/A for mouse in Streamlit, but ensure click targets are large enough
- **Wayfinding**: Clear section headers, breadcrumb-like context ("Solution #X of Y"), always show "back to top" not needed if tabs used
- **Empty/edge states**: If no feasible solutions (tight constraints), explain why and suggest relaxing constraints or checking feasibility early

## 10) Accessibility
- **Keyboard**: Ensure controls are keyboard-navigable (Streamlit handles mostly)
- **Focus states**: Visible focus rings (don't remove outlines)
- **Reduced motion**: Add CSS for `prefers-reduced-motion: reduce` - disable transforms, shorten/disable transitions
- **Reduced transparency/contrast**: Respect `prefers-reduced-transparency` and `prefers-contrast: more`
- **Color**: Don't rely on color alone to distinguish (use shapes/labels)
- **Text**: Use relative units, support Dynamic Type-like scaling

## 11) Implementation Notes (Streamlit-specific)
- Put global CSS in `assets/style.css` and inject via `st.markdown(..., unsafe_allow_html=True)`
- Keep custom JS minimal; prefer CSS for micro-interactions
- Use `st.session_state` to maintain selected solution across reruns
- Plotly: use `layout` with clean fonts, grid subtle, no 3D unless necessary
- Cache heavy computations (`@st.cache_data`) where appropriate
- For velocity/springs - not directly applicable in Streamlit's server model; focus on **response, clarity, restraint**

## Quick Checklist
- [ ] System font stack, optical sizing considered
- [ ] Consistent spacing/radius/shadows
- [ ] Instant feedback on interactive elements
- [ ] Selected Pareto point clearly highlighted
- [ ] Menu table scannable, numbers aligned
- [ ] Comparison to baselines visible
- [ ] Reduced motion/transparency/contrast supported
- [ ] Empty/error states helpful
- [ ] Export clearly available
- [ ] No decorative motion that distracts from tradeoffs
