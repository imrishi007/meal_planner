import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowDownToLine, ArrowRight, CalendarDays, Check, ChevronDown, ChevronLeft, ChevronRight, CircleHelp, Coffee, Search, Soup, Utensils, X } from "lucide-react";
import { menuApi } from "./api";
import { MealImage } from "./MealImage";
import type { Horizon, Meal, MenuDay, MenuPlan, Slot } from "./types";

type Page = "home" | "menu" | "library";
const horizonOptions: { value: Horizon; title: string; detail: string }[] = [
  { value: "today", title: "Today", detail: "A menu for the rest of today" },
  { value: "tomorrow", title: "Tomorrow", detail: "A fresh plan for one day" },
  { value: "next_3_days", title: "Next 3 days", detail: "A short, flexible plan" },
  { value: "next_7_days", title: "Next 7 days", detail: "One complete week" },
  { value: "four_weeks", title: "4-week menu", detail: "Four distinct, feasible weeks" },
];
const slotOrder: Slot[] = ["breakfast", "lunch", "dinner"];
const slotLabel: Record<Slot, string> = { breakfast: "Breakfast", lunch: "Lunch", dinner: "Dinner" };

function formatMoney(value: number) { return `₹${value.toFixed(0)}`; }
function formatDate(value: string, options: Intl.DateTimeFormatOptions = { weekday: "long", day: "numeric", month: "long" }) {
  return new Intl.DateTimeFormat("en-IN", options).format(new Date(`${value}T12:00:00`));
}
function localDate() {
  const date = new Date();
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}
function planDays(plan: MenuPlan | null): MenuDay[] {
  if (!plan) return [];
  if (plan.weeks?.length) return plan.weeks.flatMap((week) => week.days);
  return plan.days ?? [];
}

function App() {
  const [page, setPage] = useState<Page>("home");
  const [plan, setPlan] = useState<MenuPlan | null>(null);
  const [apiReady, setApiReady] = useState<boolean | null>(null);
  const [dailyCostCap, setDailyCostCap] = useState<number | null>(null);
  const [loadingCurrent, setLoadingCurrent] = useState(true);
  const [generateOpen, setGenerateOpen] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [generationError, setGenerationError] = useState("");
  const [generatedMessage, setGeneratedMessage] = useState("");
  const [horizon, setHorizon] = useState<Horizon>("today");
  const [seed, setSeed] = useState(42);
  const [selectedMeal, setSelectedMeal] = useState<Meal | null>(null);
  const [selectedDate, setSelectedDate] = useState("");

  useEffect(() => {
    let active = true;
    Promise.all([menuApi.health(), menuApi.current()])
      .then(([health, response]) => { if (active) setPlan(response.plan); if (active) setDailyCostCap(health.daily_cost_cap_inr); if (active) setApiReady(true); })
      .catch(() => { if (active) setApiReady(false); })
      .finally(() => { if (active) setLoadingCurrent(false); });
    return () => { active = false; };
  }, []);

  const days = useMemo(() => planDays(plan), [plan]);
  const today = localDate();
  const todaysPlan = days.find((day) => day.date === today);
  const chosenDate = days.find((day) => day.date === selectedDate) ?? days.find((day) => day.date >= today) ?? days[0];

  async function generateMenu() {
    setGenerating(true);
    setGenerationError("");
    setGeneratedMessage("");
    try {
      const response = await menuApi.generate(horizon, seed);
      if (!response.plan?.plan_id || !response.plan.is_feasible) throw new Error("The menu service returned a plan that could not be verified.");
      setPlan(response.plan);
      setSelectedDate(response.plan.days?.[0]?.date ?? response.plan.weeks?.[0]?.days?.[0]?.date ?? "");
      setGenerateOpen(false);
      setPage(horizon === "today" ? "home" : "menu");
      setGeneratedMessage("Your new menu is ready.");
    } catch (error) {
      setGenerationError(error instanceof Error ? error.message : "Menu generation failed. Please try again.");
    } finally {
      setGenerating(false);
    }
  }

  function downloadPlan() {
    if (!plan) return;
    const blob = new Blob([JSON.stringify(plan, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `mess-menu-${plan.plan_id}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  const title = page === "home" ? "Today at the mess" : page === "menu" ? "Your menu" : "Meal library";
  return (
    <div className="app-shell">
      <header className="topbar">
        <button className="brand" onClick={() => setPage("home")} aria-label="Mess Menu home"><span className="brand-mark"><Soup size={19} /></span><span>mess menu</span></button>
        <nav className="main-nav" aria-label="Main navigation">
          {([ ["home", "Home"], ["menu", "Menu"], ["library", "Meal library"] ] as [Page, string][]).map(([id, label]) => (
            <button key={id} onClick={() => setPage(id)} className={`nav-link ${page === id ? "is-active" : ""}`} aria-current={page === id ? "page" : undefined}>{label}</button>
          ))}
        </nav>
        <div className="topbar-end"><span className="today-date">{new Intl.DateTimeFormat("en-IN", { weekday: "short", day: "numeric", month: "short" }).format(new Date())}</span><button className="button button-primary button-small" onClick={() => setGenerateOpen(true)}><CalendarDays size={16} /> Plan meals</button></div>
      </header>

      <main className="page-wrap">
        <div className="page-heading"><div><h1>{title}</h1><p>{page === "home" ? formatDate(today) : page === "menu" ? "The meals you have planned, day by day." : "A closer look at what the kitchen can make."}</p></div>{page === "menu" && plan && <button className="button button-quiet" onClick={downloadPlan}><ArrowDownToLine size={16} /> Save menu</button>}</div>
        {apiReady === false && <div className="notice notice-error" role="alert"><CircleHelp size={17} /><span>Menu service is offline. Start the Python API to load meals or create a plan.</span></div>}
        {generatedMessage && <div className="notice notice-success" role="status"><Check size={17} /><span>{generatedMessage}</span><button className="notice-close" aria-label="Dismiss" onClick={() => setGeneratedMessage("")}><X size={15} /></button></div>}
        {page === "home" && <HomePage day={todaysPlan} loading={loadingCurrent} plan={plan} dailyCostCap={dailyCostCap} onGenerate={() => setGenerateOpen(true)} onMenu={(date) => { if (date) setSelectedDate(date); setPage("menu"); }} onLibrary={() => setPage("library")} onMeal={setSelectedMeal} />}
        {page === "menu" && <MenuPage days={days} plan={plan} dailyCostCap={dailyCostCap} selectedDate={chosenDate?.date ?? ""} onSelectDate={setSelectedDate} onGenerate={() => setGenerateOpen(true)} onMeal={setSelectedMeal} />}
        {page === "library" && <LibraryPage onMeal={setSelectedMeal} />}
      </main>

      <footer className="app-footer"><span>Made for the everyday mess menu.</span><span>Nutrition values are estimates from the project dataset.</span></footer>

      {generateOpen && <GenerateDialog horizon={horizon} onHorizon={setHorizon} seed={seed} onSeed={setSeed} busy={generating} error={generationError} onClose={() => { if (!generating) { setGenerateOpen(false); setGenerationError(""); } }} onGenerate={generateMenu} />}
      {selectedMeal && <MealDialog meal={selectedMeal} onClose={() => setSelectedMeal(null)} />}
    </div>
  );
}

function HomePage({ day, loading, plan, dailyCostCap, onGenerate, onMenu, onLibrary, onMeal }: { day?: MenuDay; loading: boolean; plan: MenuPlan | null; dailyCostCap: number | null; onGenerate: () => void; onMenu: (date?: string) => void; onLibrary: () => void; onMeal: (meal: Meal) => void }) {
  const knownPlan = Boolean(plan);
  return (
    <section className="home-layout">
      <div className="today-column">
        {loading ? <div className="loading-panel" role="status"><span className="spinner" />Checking today's menu…</div> : day ? <>
          <div className="today-intro"><span className="status-line"><span className="status-dot" />Today's menu</span><span className="date-full">{formatDate(day.date)}</span></div>
          <div className="today-meals">{slotOrder.map((slot, index) => {
            const meal = day.meals.find((entry) => entry.slot === slot);
            if (!meal) return null;
            return <MealCard key={meal.meal_id + slot} meal={meal} slot={slot} onClick={() => onMeal(meal)} featured={index === 1} />;
          })}</div>
          <div className="daily-summary"><div><span>Daily cost{dailyCostCap === null ? "" : ` · ${formatMoney(dailyCostCap)} cap`}</span><strong>{formatMoney(day.daily_cost)}{dailyCostCap === null ? "" : ` / ${formatMoney(dailyCostCap)}`}</strong></div><div><span>Estimated energy</span><strong>{Math.round(day.daily_calories).toLocaleString("en-IN")} kcal</strong></div><div><span>Estimated protein</span><strong>{day.daily_protein.toFixed(0)} g</strong></div></div>
          <p className="nutrition-note">These values are estimates. A menu meeting the 1,500 kcal minimum may still be below the 2,000 kcal optimization target.</p>
        </> : <div className="empty-today"><div className="empty-art"><div className="empty-plate"><Utensils size={36} /></div><span className="plate-accent plate-accent-one"/><span className="plate-accent plate-accent-two"/></div><div className="empty-copy"><span className="status-line"><span className="status-dot status-dot-muted" />No menu saved for today</span><h2>{knownPlan ? "Your saved plan starts on another day." : "What's cooking today?"}</h2><p>Generate a menu to see meals that fit the mess's cost, nutrition and variety rules.</p><button className="button button-primary" onClick={onGenerate}>Generate today's menu <ArrowRight size={17} /></button></div></div>}
      </div>
      <aside className="side-column">
        <div className="side-panel week-panel"><div className="side-panel-heading"><div><span className="eyebrow">Coming up</span><h2>{plan?.horizon === "four_weeks" ? "Four weeks ahead" : "The rest of your plan"}</h2></div><CalendarDays size={18} /></div>
          {plan && planDays(plan).length ? <>
            <div className="mini-week-list">{planDays(plan).slice(0, 5).map((item) => <button className="mini-day" key={item.date} onClick={() => onMenu(item.date)}><span className="mini-date"><b>{new Intl.DateTimeFormat("en-IN", { weekday: "short" }).format(new Date(`${item.date}T12:00:00`))}</b><small>{new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short" }).format(new Date(`${item.date}T12:00:00`))}</small></span><span className="mini-meal-name">{item.meals[1]?.meal_name ?? "Menu ready"}</span><span className="mini-cost">{formatMoney(item.daily_cost)}</span></button>)}</div>
            <button className="text-link" onClick={() => onMenu(planDays(plan)[0]?.date)}>See the full menu <ArrowRight size={15} /></button>
          </> : <div className="side-empty"><p>Your upcoming meals will appear here.</p><button className="text-link" onClick={onGenerate}>Plan the week <ArrowRight size={15} /></button></div>}
        </div>
        <button className="browse-panel" onClick={onLibrary}><span className="browse-icon"><Coffee size={19} /></span><span><b>Curious about the menu?</b><small>Browse all 200 meal options</small></span><ArrowRight size={17} /></button>
        <div className="honesty-card"><CircleHelp size={16} /><p>Nutrition is estimated from the dataset. Meal images are illustrative, not photos of the mess's exact preparation.</p></div>
      </aside>
    </section>
  );
}

function MealCard({ meal, slot, onClick, featured = false }: { meal: Meal; slot: Slot; onClick: () => void; featured?: boolean }) {
  return <button className={`meal-card ${featured ? "meal-card-featured" : ""} slot-${slot}`} onClick={onClick} aria-label={`View ${meal.meal_name}, ${slotLabel[slot]}`}>
    <MealImage meal={meal} className="meal-card-image" />
    <div className="meal-card-copy"><span className="meal-slot-label">{slotLabel[slot]}<span className="meal-time">{slot === "breakfast" ? "7–9 am" : slot === "lunch" ? "12–2 pm" : "7–9 pm"}</span></span><h3>{meal.meal_name}</h3><span className="meal-cuisine">{meal.cuisine}</span><div className="meal-meta"><span>{formatMoney(meal.cost)}</span><span>{Math.round(meal.calories)} kcal</span><span>{meal.protein.toFixed(0)} g protein</span></div></div><ChevronRight className="meal-card-chevron" size={18} />
  </button>;
}

function MenuPage({ days, plan, dailyCostCap, selectedDate, onSelectDate, onGenerate, onMeal }: { days: MenuDay[]; plan: MenuPlan | null; dailyCostCap: number | null; selectedDate: string; onSelectDate: (value: string) => void; onGenerate: () => void; onMeal: (meal: Meal) => void }) {
  const selected = days.find((day) => day.date === selectedDate) ?? days[0];
  const activeIndex = Math.max(0, days.findIndex((day) => day.date === selected?.date));
  const groupStart = plan?.horizon === "four_weeks" ? Math.floor(activeIndex / 7) * 7 : 0;
  const groupDays = days.slice(groupStart, groupStart + 7);
  if (!days.length) return <EmptyState title="Your menu is waiting" body="Generate a day, a week, or a four-week plan. The current plan stays saved until a new one is ready." action="Generate a menu" onAction={onGenerate} />;
  if (!selected) return null;
  const weekNumber = plan?.horizon === "four_weeks" ? Math.floor(activeIndex / 7) + 1 : 1;
  return <section className="menu-view">
    <div className="menu-toolbar"><div className="toolbar-caption"><span className="eyebrow">{plan?.horizon === "four_weeks" ? `Week ${weekNumber} of 4` : horizonOptions.find((item) => item.value === plan?.horizon)?.title ?? "Your plan"}</span><span className="toolbar-detail">{formatDate(groupDays[0]?.date ?? selected.date, { day: "numeric", month: "short" })} – {formatDate(groupDays[groupDays.length - 1]?.date ?? selected.date, { day: "numeric", month: "short" })}</span></div><div className="toolbar-actions">{plan && <span className="feasible-label"><Check size={15} /> Rules checked</span>}<button className="button button-primary button-small" onClick={onGenerate}>Make a new menu</button></div></div>
    {plan?.horizon === "four_weeks" && <div className="week-switch" aria-label="Choose week">{Array.from({ length: 4 }, (_, index) => <button key={index} onClick={() => onSelectDate(days[index * 7]?.date ?? "")} className={weekNumber === index + 1 ? "selected" : ""}>Week {index + 1}</button>)}</div>}
    <div className="day-rail" aria-label="Choose a day">{groupDays.map((day) => <button key={day.date} className={`day-chip ${selected.date === day.date ? "selected" : ""}`} onClick={() => onSelectDate(day.date)}><span>{new Intl.DateTimeFormat("en-IN", { weekday: "short" }).format(new Date(`${day.date}T12:00:00`))}</span><b>{new Intl.DateTimeFormat("en-IN", { day: "numeric" }).format(new Date(`${day.date}T12:00:00`))}</b></button>)}</div>
    <div className="day-heading"><div><span className="eyebrow">{selected.day_name}</span><h2>{formatDate(selected.date, { day: "numeric", month: "long" })}</h2></div><div className="day-arrows"><button aria-label="Previous day" onClick={() => onSelectDate(days[Math.max(0, activeIndex - 1)].date)} disabled={activeIndex === 0}><ChevronLeft size={18} /></button><button aria-label="Next day" onClick={() => onSelectDate(days[Math.min(days.length - 1, activeIndex + 1)].date)} disabled={activeIndex === days.length - 1}><ChevronRight size={18} /></button></div></div>
    <div className="menu-day-grid">{slotOrder.map((slot, index) => { const meal = selected.meals.find((entry) => entry.slot === slot); return meal ? <MealCard key={meal.meal_id + slot} meal={meal} slot={slot} onClick={() => onMeal(meal)} featured={index === 1} /> : null; })}</div>
    <div className="day-summary"><div className="day-summary-title"><span>For this day</span><small>Estimated totals</small></div><div><b>{formatMoney(selected.daily_cost)}{dailyCostCap === null ? "" : ` / ${formatMoney(dailyCostCap)}`}</b><small>cost{dailyCostCap === null ? "" : " · daily cap"}</small></div><div><b>{Math.round(selected.daily_calories).toLocaleString("en-IN")} kcal</b><small>energy</small></div><div><b>{selected.daily_protein.toFixed(0)} g</b><small>protein</small></div></div>
    {plan?.horizon === "four_weeks" && plan.pairwise_differences && <div className="diversity-note"><Check size={16} /><span>All four weeks meet the {String(plan.settings.min_differing_slots ?? 7)}-meal variety rule. Each week differs by at least that many meal slots.</span></div>}
    {plan?.horizon === "four_weeks" && plan.weeks && <WeekComparison weeks={plan.weeks} selectedWeek={weekNumber} differences={plan.pairwise_differences ?? []} minimum={Number(plan.settings.min_differing_slots ?? 7)} />}
  </section>;
}

function WeekComparison({ weeks, selectedWeek, differences, minimum }: { weeks: NonNullable<MenuPlan["weeks"]>; selectedWeek: number; differences: NonNullable<MenuPlan["pairwise_differences"]>; minimum: number }) {
  const compared = differences.filter((pair) => pair.week_a === selectedWeek || pair.week_b === selectedWeek);
  const average = (weekNumber: number, key: "daily_cost" | "daily_calories" | "daily_protein") => {
    const selected = weeks.find((week) => week.week_number === weekNumber);
    if (!selected?.days.length) return 0;
    return selected.days.reduce((total, day) => total + day[key], 0) / selected.days.length;
  };
  return <section className="week-comparison" aria-label="Four week comparison"><div className="comparison-heading"><div><span className="eyebrow">The month, at a glance</span><h3>Week-to-week comparison</h3></div><span>All totals are estimates</span></div>
    <div className="comparison-weeks">{weeks.map((week) => {
      const cost = week.days.reduce((total, day) => total + day.daily_cost, 0);
      const calories = week.days.reduce((total, day) => total + day.daily_calories, 0) / Math.max(week.days.length, 1);
      const protein = week.days.reduce((total, day) => total + day.daily_protein, 0) / Math.max(week.days.length, 1);
      return <div key={week.week_number} className={`comparison-week ${week.week_number === selectedWeek ? "active" : ""}`}><b>Week {week.week_number}</b><span>₹{cost.toFixed(0)} total</span><small>{Math.round(calories).toLocaleString("en-IN")} kcal/day · {protein.toFixed(0)} g protein/day</small></div>;
    })}</div>
    <div className="pair-differences"><b>Compared with Week {selectedWeek}</b>{compared.length ? compared.map((pair) => {
      const other = pair.week_a === selectedWeek ? pair.week_b : pair.week_a;
      const costDelta = average(other, "daily_cost") - average(selectedWeek, "daily_cost");
      const calorieDelta = average(other, "daily_calories") - average(selectedWeek, "daily_calories");
      const proteinDelta = average(other, "daily_protein") - average(selectedWeek, "daily_protein");
      const signed = (value: number, precision = 0) => `${value >= 0 ? "+" : "−"}${Math.abs(value).toFixed(precision)}`;
      return <div key={`${pair.week_a}-${pair.week_b}`}><span>Week {pair.week_a} ↔ Week {pair.week_b}</span><strong>{pair.different_slots} different slots · {pair.different_slots >= minimum ? "rule met" : "below rule"}</strong><small>Daily difference: {signed(costDelta)} ₹ · {signed(calorieDelta)} kcal · {signed(proteinDelta)} g protein</small></div>;
    }) : <span className="pair-self">Select a different week to compare variety.</span>}</div>
  </section>;
}

function LibraryPage({ onMeal }: { onMeal: (meal: Meal) => void }) {
  const [meals, setMeals] = useState<Meal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [cuisine, setCuisine] = useState("All cuisines");
  const [slot, setSlot] = useState("All meal times");
  useEffect(() => {
    let active = true;
    menuApi.meals().then((result) => { if (active) setMeals(result.meals); }).catch((issue) => { if (active) setError(issue instanceof Error ? issue.message : "Meals could not be loaded."); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);
  const cuisines = useMemo(() => ["All cuisines", ...Array.from(new Set(meals.map((meal) => meal.cuisine))).sort()], [meals]);
  const filtered = meals.filter((meal) => meal.meal_name.toLowerCase().includes(query.toLowerCase()) && (cuisine === "All cuisines" || meal.cuisine === cuisine) && (slot === "All meal times" || meal.suitable_meal_types.includes(slot as Slot)));
  return <section className="library-view">
    <div className="library-tools"><label className="search-box"><Search size={17} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Find a dish" aria-label="Search meals" /></label><label className="select-box"><span className="sr-only">Filter by cuisine</span><select value={cuisine} onChange={(event) => setCuisine(event.target.value)}>{cuisines.map((item) => <option key={item}>{item}</option>)}</select><ChevronDown size={15} /></label><label className="select-box"><span className="sr-only">Filter by meal time</span><select value={slot} onChange={(event) => setSlot(event.target.value)}>{["All meal times", "breakfast", "lunch", "dinner"].map((item) => <option key={item} value={item}>{item === "All meal times" ? item : slotLabel[item as Slot]}</option>)}</select><ChevronDown size={15} /></label><span className="result-count">{loading ? "Loading meals…" : `${filtered.length} meals`}</span></div>
    {error && <div className="notice notice-error" role="alert"><CircleHelp size={16} />{error}</div>}
    {!loading && !error && !filtered.length && <EmptyState title="No meals match those filters" body="Try a different name, cuisine, or meal time." action="Clear filters" onAction={() => { setQuery(""); setCuisine("All cuisines"); setSlot("All meal times"); }} />}
    {loading && <div className="loading-panel" role="status"><span className="spinner" />Loading the meal library…</div>}
    <div className="library-grid">{filtered.map((meal) => <button className="library-card" key={meal.meal_id} onClick={() => onMeal(meal)}><MealImage meal={meal} className="library-card-image" /><span className="library-card-copy"><span className="meal-cuisine">{meal.cuisine}</span><b>{meal.meal_name}</b><span className="library-card-meta"><span>{formatMoney(meal.cost)}</span><span>{Math.round(meal.calories)} kcal</span><span>{meal.protein.toFixed(0)} g protein</span></span></span><span className="sr-only">Meal ID {meal.meal_id}</span></button>)}</div>
    <p className="library-disclaimer">Meal ratings are synthetic project data. Images are representative illustrations, not photographs of the hostel preparation.</p>
  </section>;
}

function GenerateDialog({ horizon, onHorizon, seed, onSeed, busy, error, onClose, onGenerate }: { horizon: Horizon; onHorizon: (value: Horizon) => void; seed: number; onSeed: (value: number) => void; busy: boolean; error: string; onClose: () => void; onGenerate: () => void }) {
  const dialogRef = useRef<HTMLElement>(null);
  useEffect(() => {
    const dialog = dialogRef.current;
    const previousFocus = document.activeElement as HTMLElement | null;
    dialog?.querySelector<HTMLElement>("button:not([disabled]), input:not([disabled])")?.focus();
    const handle = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !busy) onClose();
      if (event.key === "Tab" && dialog) keepFocusInside(event, dialog);
    };
    window.addEventListener("keydown", handle);
    return () => { window.removeEventListener("keydown", handle); previousFocus?.focus(); };
  }, [busy, onClose]);
  return <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget && !busy) onClose(); }}><section ref={dialogRef} tabIndex={-1} className="generate-dialog" role="dialog" aria-modal="true" aria-labelledby="generate-title"><div className="dialog-top"><div><span className="eyebrow">A menu that works for the mess</span><h2 id="generate-title">What would you like to plan?</h2><p>We’ll find a menu that fits the mess’s daily rules.</p></div><button className="icon-button" onClick={onClose} disabled={busy} aria-label="Close"><X size={19} /></button></div>
    <div className="horizon-options" role="radiogroup" aria-label="Menu length">{horizonOptions.map((option) => <button key={option.value} role="radio" aria-checked={horizon === option.value} className={`horizon-option ${horizon === option.value ? "selected" : ""}`} onClick={() => onHorizon(option.value)}><span className="radio-dot"/><span><b>{option.title}</b><small>{option.detail}</small></span>{horizon === option.value && <Check size={16} />}</button>)}</div>
    <label className="seed-label">Random seed <span>Optional — reuse a number to repeat a run</span><input type="number" min="0" max="2147483647" value={seed} onChange={(event) => onSeed(Math.max(0, Number(event.target.value) || 0))} disabled={busy} /></label>
    <p className="dialog-note"><CircleHelp size={15} /> Generated meals follow the current meal-time, daily calorie, budget, and variety rules. Nutrition values are estimates.</p>
    {error && <div className="notice notice-error dialog-error" role="alert">{error}</div>}
    <div className="dialog-actions"><button className="button button-quiet" onClick={onClose} disabled={busy}>Cancel</button><button className="button button-primary" onClick={onGenerate} disabled={busy}>{busy ? <><span className="button-spinner"/> Finding your menu…</> : <>Generate my menu <ArrowRight size={17} /></>}</button></div>
  </section></div>;
}

function MealDialog({ meal, onClose }: { meal: Meal; onClose: () => void }) {
  const dialogRef = useRef<HTMLElement>(null);
  useEffect(() => {
    const dialog = dialogRef.current;
    const previousFocus = document.activeElement as HTMLElement | null;
    dialog?.querySelector<HTMLElement>("button:not([disabled])")?.focus();
    const handle = (event: KeyboardEvent) => { if (event.key === "Escape") onClose(); if (event.key === "Tab" && dialog) keepFocusInside(event, dialog); };
    window.addEventListener("keydown", handle);
    return () => { window.removeEventListener("keydown", handle); previousFocus?.focus(); };
  }, [onClose]);
  return <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}><section ref={dialogRef} tabIndex={-1} className="meal-dialog" role="dialog" aria-modal="true" aria-labelledby="meal-dialog-title"><button className="icon-button meal-dialog-close" onClick={onClose} aria-label="Close meal details"><X size={19} /></button><MealImage meal={meal} className="meal-dialog-image"/><div className="meal-dialog-body"><span className="meal-cuisine">{meal.cuisine} · {meal.meal_id}</span><h2 id="meal-dialog-title">{meal.meal_name}</h2><p className="meal-dialog-slots">Available for {meal.suitable_meal_types.map((item) => slotLabel[item]).join(", ")}</p><div className="detail-nutrients"><div><small>Serving cost</small><b>{formatMoney(meal.cost)}</b></div><div><small>Energy estimate</small><b>{Math.round(meal.calories)} kcal</b></div><div><small>Protein estimate</small><b>{meal.protein.toFixed(1)} g</b></div><div><small>Carbohydrates · fat</small><b>{meal.carbs.toFixed(0)} g · {meal.fat.toFixed(0)} g</b></div><div><small>Preparation estimate</small><b>{meal.prep_time_minutes} min · {meal.kitchen_load} load</b></div><div><small>Student rating</small><b>{meal.rating.toFixed(1)} / 5 · {meal.rating_source}</b></div></div><div className="meal-components"><span>Meal components</span><p>{meal.meal_components.join(" · ")}</p><small>Allergens listed: {meal.allergens || "Not specified"}</small></div><p className="meal-dialog-note">Nutrition values are estimates. This image represents the dish and is not a photo of the exact preparation.</p></div></section></div>;
}

function keepFocusInside(event: KeyboardEvent, dialog: HTMLElement) {
  const targets = Array.from(dialog.querySelectorAll<HTMLElement>("button:not([disabled]), input:not([disabled]), select:not([disabled]), a[href]"));
  const first = targets[0];
  const last = targets[targets.length - 1];
  if (!first || !last) { event.preventDefault(); dialog.focus(); return; }
  if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
  else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
}

function EmptyState({ title, body, action, onAction }: { title: string; body: string; action: string; onAction: () => void }) {
  return <div className="empty-state"><div className="empty-state-mark"><CalendarDays size={25} /></div><h2>{title}</h2><p>{body}</p><button className="button button-primary" onClick={onAction}>{action}<ArrowRight size={17} /></button></div>;
}

export default App;
