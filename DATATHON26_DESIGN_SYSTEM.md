# Datathon26 Complete Design System & Visual Language Reference

> **Source Project:** `Datathon26` / `CrimeNexus` (`/Users/krishanand/datathon26`)  
> **Tech Stack of Reference:** Next.js 16 (App Router), React 19, Tailwind CSS v4, Lucide React, Recharts, @xyflow/react  
> **Purpose:** Standalone visual identity, component styling guide, and design token reference for replicating the Datathon26 visual design language in other dashboards and applications.

---

## 1. Overall Theme

* **Main Design Concept:** Mission-critical cyber intelligence operations console / high-tech law enforcement command center.
* **Visual Identity:** Deep obsidian canvas, glassmorphic slate cards with subtle inset rim lighting, electric indigo accents, cyan telemetry data, and glowing status indicators.
* **Overall Mood and Aesthetic:** Serious, tactical, high-contrast, data-dense, futuristic yet clean and highly legible.
* **Styling Classification:** **Futuristic Dark Glassmorphism with Dense Micro-Accents**. It rejects flat matte dark themes in favor of multi-layered translucent surfaces (`backdrop-blur-xl`), delicate border alpha channels (`border-slate-800/60`), and ambient colored radial lighting spheres in the background.
* **Communicating Project Purpose:** The design communicates real-time situational awareness through pulsing live status beacons (`ONLINE`), high-contrast monospace timestamps/IDs, micro-badges with tight letter-spacing, and clear color-coded severity metrics.

---

## 2. Color System

### Canvas & Surface Colors
| Role / Element | Exact Hex / RGBA | Tailwind / CSS Class | Purpose |
| :--- | :--- | :--- | :--- |
| **Root Background** | `#070b13` | `bg-[#070b13]`, `var(--background)` | Entire screen backdrop |
| **Radial Glow Center** | `#0d1527` | `bg-radial from-[#0d1527] to-[#070b13]` | Page ambient gradient fill |
| **Sidebar Surface** | `#0a0f1d` (98% op) | `bg-[#0a0f1d]/98` | Fixed sidebar backdrop |
| **Glass Card Fill** | `rgba(15, 23, 42, 0.45)` | `.glass-card`, `bg-slate-900/60` | Card, widget, and panel surface |
| **Glass Card Inset Rim** | `rgba(255, 255, 255, 0.03)` | `inset 0 1px 0 rgba(255, 255, 255, 0.03)` | Top-edge specular highlight |
| **Input / Field Fill** | `#020617` / `#0f172a` | `bg-slate-950`, `bg-slate-900/60` | Search bars, inputs, select dropdowns |
| **Tooltip / Popover** | `#0f172a` (95% op) | `bg-[#0f172a]/95` | Recharts tooltips & flyouts |

### Brand & Interactive Colors
| Role / Element | Exact Hex / RGBA | Tailwind / CSS Class | Purpose |
| :--- | :--- | :--- | :--- |
| **Primary Accent** | `#6366f1` | `text-indigo-400`, `bg-indigo-600` | Primary action buttons, active navigation, focus rings |
| **Primary Hover** | `#4f46e5` / `#818cf8` | `hover:bg-indigo-500`, `hover:text-indigo-300` | Interactive hover states |
| **Primary Tint (Glow/Badge)** | `rgba(99, 102, 241, 0.10)` | `bg-indigo-500/10`, `border-indigo-500/20` | Icon boxes, category tags, badges |
| **Secondary Accent** | `#22d3ee` | `text-cyan-400`, `fill="#22d3ee"` | Geographic/district telemetry, chargesheet badges |
| **Tertiary Accent** | `#a78bfa` | `text-violet-400`, `bg-violet-500/10` | Network graphs, inspector tabs, categorical series |

### Semantic & Status Palette
| State / Severity | Hex Code | Text Class | Background Pill | Border Class |
| :--- | :--- | :--- | :--- | :--- |
| **Critical / High Danger** | `#f87171` / `#ef4444` | `text-red-400`, `text-red-500` | `bg-red-500/10` or `/20` | `border-red-500/20` or `/30` |
| **Warning / Medium Severity**| `#fbbf24` / `#f59e0b` | `text-amber-400` | `bg-amber-500/10` or `/20` | `border-amber-500/20` or `/30` |
| **Success / Low / Resolved** | `#34d399` / `#22c55e` | `text-emerald-400`, `text-green-400` | `bg-emerald-500/10` or `/20` | `border-emerald-500/20` or `/30` |
| **Investigating / Processing**| `#6366f1` / `#3b82f6` | `text-indigo-400`, `text-blue-400` | `bg-indigo-500/20`, `bg-blue-500/10` | `border-indigo-500/30`, `border-blue-500/20` |
| **Neutral / Dismissed** | `#64748b` | `text-slate-400` | `bg-slate-500/10`, `bg-slate-800/60` | `border-slate-500/20`, `border-slate-800/60` |

### Text Color Hierarchy
* **Headings / High-Impact Numbers:** `#f8fafc` (`text-slate-50`, `text-slate-100`, `text-white`)
* **Body Text / Primary Values:** `#e2e8f0` (`text-slate-200`, `text-slate-300`)
* **Secondary Text / Descriptions:** `#94a3b8` (`text-slate-400`)
* **Muted Metadata / Field Labels:** `#64748b` (`text-slate-500`)
* **Faint Subtitles / Dividers:** `#475569` (`text-slate-600`, `text-slate-700`)

---

## 3. Typography

* **Primary Font Family:** Inter (`var(--font-inter), system-ui, -apple-system, sans-serif`)
* **Data & Numerical Font Family:** Monospace (`font-mono`) for timestamps, coordinates, and system IDs.

### Typography Scale
| Element | Font Size | Font Weight | Letter Spacing & Transform | Color | Example Usage |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Page Title (`<h1>`)** | `text-2xl` to `text-3xl` (24–30px) | `font-black` (900) or `font-extrabold` (800) | `uppercase tracking-tight leading-tight` | `text-slate-100` | `"COMMAND CENTER"` |
| **Section Title (`<h3>`)**| `text-sm` (14px) | `font-bold` (700) | `uppercase tracking-wider leading-none` | `text-slate-200` | `"RECENT CRIME EVENTS"` |
| **Widget / Metric Value**| `text-3xl` (30px) | `font-black` (900) or `font-extrabold` | `tracking-tight leading-none` | `text-slate-50` or `font-mono` | `14,820`, `74.5%` |
| **Field / Column Label** | `text-[10px]` or `text-[11px]` | `font-bold` (700) | `uppercase tracking-wider` | `text-slate-400` / `text-slate-500` | `"CRIME TYPE"`, `"DATA VOLUME"` |
| **Micro-Badge / Tag** | `text-[9px]` or `text-[10px]` | `font-black` (900) or `font-extrabold` | `uppercase tracking-widest` | Status Color | `"CRITICAL"`, `"ONLINE"` |
| **Table Cells / Body** | `text-xs` (12px) to `text-sm` (14px) | `font-medium` (500) | Normal / `leading-relaxed` | `text-slate-300` / `text-slate-400` | Row values, descriptions |
| **Monospace Identifiers**| `text-xs` (12px) | `font-mono font-bold` | `tracking-wider` | `text-slate-400` / `text-indigo-400` | Dates, crime IDs |

---

## 4. UI Components

### 1. Fixed Collapsible Sidebar
* **Dimensions:** Fixed to left viewport edge. Expanded: `w-64` (256px); Collapsed: `w-[4.5rem]` (72px). Smooth transition: `transition-[width] duration-300 ease-out`.
* **Surface:** `bg-[#0a0f1d]/98 border-r border-[#1e293b]/70 backdrop-blur-xl shadow-2xl shadow-black/30`.
* **Brand Header:**
  * Logo container: `w-10 h-10 object-contain rounded-lg`.
  * Title: `font-bold text-sm text-slate-100 tracking-wider`.
  * Sub-badge: `text-[10px] text-indigo-400 font-semibold tracking-widest`.
  * Pin toggle: `p-2 rounded-lg border border-slate-800 bg-slate-950/60 text-slate-500 hover:text-indigo-300 hover:border-indigo-500/30`.
* **Nav Section Headers:** `text-[9px] uppercase font-bold text-slate-600 tracking-widest px-3 mb-2`.
* **Nav Items:**
  * *Default:* `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-slate-400 hover:bg-slate-800/50 hover:text-slate-200 border border-transparent transition-all duration-200`.
  * *Active:* `bg-indigo-600/10 text-indigo-400 border-indigo-500/20 shadow-[inset_0_1px_0_rgba(99,102,241,0.1)]`.
  * *Icon styling:* `w-4 h-4 shrink-0`. Inactive: `text-slate-500 group-hover:text-slate-300`; Active: `text-indigo-400`.

### 2. Sticky Navbar
* **Dimensions:** Height `h-14` (56px), `sticky top-0 z-40 px-6`.
* **Surface:** `bg-[#070b13]/90 backdrop-blur-md border-b border-slate-800/60`.
* **API Live Indicator:** `flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-900/80 border border-slate-800/60 text-xs`. Features green pulsing dot + `text-emerald-400 font-bold`.
* **Breadcrumb:** `text-xs text-slate-500` with separators `text-slate-700` and current page `font-semibold text-slate-300`.
* **Icon Actions:** `p-2 rounded-lg text-slate-500 hover:text-slate-200 hover:bg-slate-800/60 transition-colors relative`. Notification unread dot: `absolute top-1.5 right-1.5 w-1.5 h-1.5 bg-indigo-500 rounded-full`.

### 3. Glass Card Container (`.glass-card`)
* **Shape & Corners:** `rounded-2xl` (16px) or `rounded-3xl` (24px).
* **Border:** `1px solid rgba(30, 41, 59, 0.5)` (`border-slate-800/60`).
* **Background:** `rgba(15, 23, 42, 0.45)` with `backdrop-filter: blur(12px)`.
* **Shadow:** `box-shadow: 0 4px 24px rgba(0, 0, 0, 0.25), inset 0 1px 0 rgba(255, 255, 255, 0.03)`.
* **Hover State:** Border transitions to `rgba(99, 102, 241, 0.2)` with outer glow `0 0 20px -8px rgba(99, 102, 241, 0.1)`.

### 4. Section Header (Signature Anchor)
```tsx
<div className="flex items-center gap-2.5 mb-5">
  <div className="w-1 h-[18px] bg-indigo-500 rounded-sm shrink-0" />
  <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider leading-none">
    {title}
  </h3>
</div>
```

### 5. KPI Cards
* **Container:** `glass-card p-6 rounded-2xl border border-slate-800/60 flex flex-col justify-between min-h-[140px] relative overflow-hidden transition-all duration-300`.
* **Header:** Left label `text-[11px] font-bold text-slate-400 uppercase tracking-wider`; Right icon container `p-2.5 rounded-xl border bg-indigo-500/10 border-indigo-500/20 text-indigo-400`.
* **Value & Subtitle:** Number `text-3xl font-extrabold text-slate-50 tracking-tight leading-none mt-2`; Subtitle `text-[10px] text-slate-500 font-semibold tracking-wider mt-1 uppercase`.
* **Hover State:** `hover:border-indigo-500/40 hover:shadow-[0_0_15px_rgba(99,102,241,0.15)]`.

### 6. System Status Bar (Telemetry Row)
* **Container:** `glass-card p-5 rounded-xl border border-slate-800/60 flex flex-col md:flex-row justify-between items-stretch md:items-center gap-4 divide-y md:divide-y-0 md:divide-x divide-slate-800/60`.
* **Live Beacon Element:**
  ```tsx
  <div className="relative flex h-2 w-2">
    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
    <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
  </div>
  ```

### 7. Tables
* **Wrapper:** `glass-card p-6 rounded-2xl border border-slate-800/60 overflow-x-auto`.
* **Header (`<thead>`):** `bg-slate-900/60 border-b border-slate-800`.
* **Header Cells (`<th>`):** `px-4 py-3 text-left text-xs font-bold text-slate-400 uppercase tracking-wider`.
* **Rows (`<tr>`):** `border-b border-slate-800/45 hover:bg-slate-800/30 even:bg-slate-900/10 transition-colors`.
* **Data Cells (`<td>`):** `px-4 py-3.5 text-xs text-slate-400 font-mono` or `text-xs font-bold text-slate-100 uppercase tracking-tight`.

### 8. Badges & Pills
* **General Shape:** `inline-flex items-center px-2 py-0.5 rounded-full text-[9px] or text-[10px] font-bold border uppercase tracking-wider`.
* **Critical:** `bg-red-500/10 border-red-500/30 text-red-400 flex items-center gap-1`.
* **Warning:** `bg-amber-500/10 border-amber-500/20 text-amber-400`.
* **Success / Online:** `bg-green-500/20 border-green-500/30 text-green-400`.
* **Investigating:** `bg-indigo-500/20 border-indigo-500/30 text-indigo-400`.
* **Chargesheet / Regional:** `bg-cyan-500/20 border-cyan-500/30 text-cyan-400`.

### 9. Buttons
* **Primary Solid CTA:** `px-6 py-3 bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs sm:text-sm uppercase tracking-wider rounded-xl transition-all duration-200 shadow-lg shadow-indigo-600/20 cursor-pointer disabled:opacity-50 flex items-center gap-2`.
* **Gradient Button:** `bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 border border-indigo-500/20 text-white rounded-xl text-xs font-black uppercase tracking-wider shadow-lg shadow-indigo-600/10 transition-all`.
* **Secondary Ghost:** `px-4 py-2.5 bg-slate-900 hover:bg-slate-850 border border-slate-800 hover:border-slate-700 text-slate-300 hover:text-slate-100 font-extrabold text-xs uppercase tracking-wider rounded-xl transition-all`.
* **Danger Button:** `px-6 py-2.5 bg-red-600 hover:bg-red-700 text-white rounded-xl text-xs font-bold uppercase tracking-wider transition-all`.

### 10. Forms, Inputs & Dropdowns
* **Input Field:** `w-full bg-slate-900/60 border border-slate-700/60 text-slate-200 text-sm rounded-lg px-3 py-2.5 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30 transition-colors placeholder:text-slate-600 outline-none font-medium`.
* **Search Field:** `w-full pl-10 pr-4 py-2 bg-slate-950 border border-slate-900 rounded-xl text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-slate-800 transition-all font-medium`.
* **Select Dropdown:** `appearance-none bg-slate-950 border border-slate-900 rounded-xl pl-4 pr-10 py-2 text-[11px] font-semibold text-slate-300 focus:outline-none focus:border-slate-800 cursor-pointer`.
* **Field Labels:** `block text-[10px] sm:text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1.5`.

### 11. Tabs & Segmented Switchers
* **Pill Segmented Controls (Granularity / Filters):**
  * Container: `flex bg-slate-900/60 p-1 rounded-xl border border-slate-800/50`.
  * Active: `px-3 py-1.5 rounded-lg text-xs font-bold bg-indigo-600 text-white shadow-md`.
  * Inactive: `px-3 py-1.5 rounded-lg text-xs font-bold text-slate-400 hover:text-slate-200`.
* **Underline Navigation Tabs:**
  * Container: `flex border-b border-slate-900 gap-2`.
  * Active: `pb-4 px-4 text-xs uppercase tracking-widest font-black text-indigo-400 border-b-2 border-indigo-500`.
  * Inactive: `pb-4 px-4 text-xs uppercase tracking-widest font-black text-slate-500 hover:text-slate-300 border-transparent`.

### 12. Modals & Dialogs
* **Backdrop:** `fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4`.
* **Modal Body:** `bg-slate-900 border border-slate-800 rounded-3xl w-full max-w-5xl shadow-2xl relative animate-zoom-in text-slate-200`.
* **Header:** `p-6 border-b border-slate-800 flex items-center justify-between`.
* **Footer:** `p-6 border-t border-slate-800 flex justify-end gap-3`.

### 13. Charts (Recharts)
* **Cartesian Grid:** `stroke="#1e293b" strokeDasharray="3 3"` (vertical lines turned off).
* **Axes:** `tick={{ fill: "#94a3b8", fontSize: 10 }}`, `tickLine={false}`, `axisLine={false}`.
* **Area Gradient Fill:**
  ```xml
  <linearGradient id="trendGradient" x1="0" y1="0" x2="0" y2="1">
    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.25} />
    <stop offset="95%" stopColor="#6366f1" stopOpacity={0.0} />
  </linearGradient>
  ```
* **Custom Tooltip:**
  ```tsx
  <div className="bg-[#0f172a] border border-[#1e293b] p-3 rounded-lg shadow-xl backdrop-blur-md">
    <p className="text-[10px] uppercase tracking-wider font-bold text-slate-500">Category</p>
    <p className="text-xs font-bold text-slate-200 mt-0.5">{label}</p>
    <p className="text-sm font-extrabold text-indigo-400 mt-1">{value} units</p>
  </div>
  ```

### 14. Loading & Skeleton States
* **Card Skeletons:** Preserves identical geometry with `animate-pulse` boxes (`bg-slate-800/50 rounded-xl`).
* **Chart Skeletons:** Animated horizontal line tracks with multiple bars of varied widths (`w-[95%]`, `w-[75%]`, `w-[50%]`).
* **Action Spinners:** `<RefreshCw className="w-4 h-4 animate-spin text-indigo-400" />`.

---

## 5. Layout & Spacing

* **Page Shell:**
  ```tsx
  <div className="flex h-screen overflow-hidden bg-[#070b13] text-slate-100 font-sans">
    <Sidebar />
    <div className={`flex flex-col flex-1 min-w-0 overflow-hidden transition-[padding] duration-300 ${sidebarPinned ? "pl-64" : "pl-[4.5rem]"}`}>
      <Navbar />
      <main className="flex-1 overflow-y-auto px-4 py-6 sm:px-6 sm:py-7 md:px-8 md:py-8 relative bg-radial from-[#0d1527] to-[#070b13] animate-fade-in">
        {children}
      </main>
    </div>
  </div>
  ```
* **Page Width Constraint:** `max-w-7xl mx-auto w-full`.
* **Standard Grid Formats:**
  * **Top KPI Row:** `grid grid-cols-2 lg:grid-cols-4 gap-4`.
  * **Main Visualizations (60/40 split):** `grid grid-cols-1 lg:grid-cols-5 gap-4` (Left: `lg:col-span-3`, Right: `lg:col-span-2`).
  * **Secondary Details Row:** Full width `w-full` stacked blocks separated by `space-y-6`.

---

## 6. Visual Effects & Micro-Interactions

### 1. Ambient Lighting Orbs
Large blurred background circles that create depth behind content without interfering with pointer events:
```tsx
<div className="absolute top-[15%] right-[5%] w-[450px] h-[450px] rounded-full bg-indigo-500/5 blur-[120px] pointer-events-none" />
<div className="absolute bottom-[10%] left-[10%] w-[350px] h-[350px] rounded-full bg-violet-500/5 blur-[100px] pointer-events-none" />
```

### 2. Keyframe Animations
```css
@keyframes fade-in {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  20%       { transform: translateX(-4px); }
  40%       { transform: translateX(4px); }
  60%       { transform: translateX(-3px); }
  80%       { transform: translateX(3px); }
}

@keyframes slide-up {
  from { opacity: 0; transform: translateY(12px); }
  to   { opacity: 1; transform: translateY(0); }
}
```

### 3. Global Focus & Scrollbars
```css
*:focus-visible {
  outline: 2px solid #6366f1;
  outline-offset: 2px;
  border-radius: 4px;
}

::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: #070b13;
}

::-webkit-scrollbar-thumb {
  background: #1e293b;
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: #334155;
}
```

---

## 7. Icons & Graphics

* **Icon Library:** `lucide-react`
* **Style:** Thin-line technical stroke icons (stroke width `1.5` to `2`).
* **Sizing Rules:**
  * Inline / Micro: `w-3 h-3` or `w-3.5 h-3.5`
  * Nav & Standard Actions: `w-4 h-4`
  * Card Header Badges: `w-5 h-5`
  * Large Empty State / Alert Heroes: `w-12 h-12` to `w-16 h-16`
* **Container Packaging:** Icons are rarely bare. They are packaged inside rounded background squares:
  `p-2.5 rounded-xl border bg-indigo-500/10 border-indigo-500/20 text-indigo-400`

---

## 8. Dashboard Patterns

1. **Header & Context Strip:** Real-time API status badge, breadcrumbs, and active workspace/dataset indicator.
2. **Top 4 KPI Metrics:** Standard 4-card metric row with count-up animation and color-coded status badges.
3. **Telemetry Bar:** Horizontal divider row with monospace numbers summarizing volume, coverage, and risk.
4. **60/40 Analytical Chart Split:** Time-series area chart on the left paired with categorical horizontal bars on the right.
5. **Full-Width Ranking Chart:** Horizontal bar chart displaying top 10 items (districts, nodes, or units).
6. **Recent Activity Table:** Responsive high-contrast table with colored status badges, monospace dates, and hover rows.
7. **Empty States (`NoDatasetBanner`):** Centered card with animated pulsing icon, clear descriptive copy, and a primary CTA button.

---

## 9. Design Tokens Summary

```json
{
  "colors": {
    "background": {
      "base": "#070b13",
      "radialCenter": "#0d1527",
      "sidebar": "#0a0f1d",
      "card": "rgba(15, 23, 42, 0.45)",
      "input": "#020617",
      "tooltip": "#0f172a"
    },
    "brand": {
      "primary": "#6366f1",
      "primaryHover": "#4f46e5",
      "primaryLight": "#818cf8",
      "primaryTint": "rgba(99, 102, 241, 0.10)",
      "secondaryCyan": "#22d3ee",
      "tertiaryViolet": "#a78bfa"
    },
    "status": {
      "emeraldSuccess": "#34d399",
      "greenSuccess": "#22c55e",
      "amberWarning": "#fbbf24",
      "redDanger": "#f87171",
      "blueInfo": "#3b82f6"
    },
    "text": {
      "heading": "#f8fafc",
      "body": "#e2e8f0",
      "muted": "#94a3b8",
      "subtle": "#64748b",
      "faint": "#475569"
    },
    "border": {
      "card": "rgba(30, 41, 59, 0.50)",
      "cardHover": "rgba(99, 102, 241, 0.20)",
      "subtle": "#1e293b",
      "active": "rgba(99, 102, 241, 0.40)"
    }
  },
  "typography": {
    "fontFamily": "Inter, system-ui, sans-serif",
    "fontMono": "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
    "headings": "font-black uppercase tracking-tight",
    "sectionLabels": "text-sm font-bold uppercase tracking-wider",
    "microLabels": "text-[10px] font-bold uppercase tracking-widest",
    "kpiValues": "text-3xl font-extrabold tracking-tight"
  },
  "spacing": {
    "pagePadding": "px-4 py-6 sm:px-6 sm:py-7 md:px-8 md:py-8",
    "sectionGap": "space-y-6 md:space-y-8",
    "gridGap": "gap-4 sm:gap-6"
  },
  "borderRadius": {
    "card": "16px (rounded-2xl) to 24px (rounded-3xl)",
    "innerElement": "12px (rounded-xl)",
    "input": "8px (rounded-lg)",
    "badge": "9999px (rounded-full)",
    "sectionBar": "2px (rounded-sm)"
  },
  "shadows": {
    "card": "0 4px 24px rgba(0, 0, 0, 0.25), inset 0 1px 0 rgba(255, 255, 255, 0.03)",
    "cardHover": "0 8px 32px -8px rgba(0, 0, 0, 0.35), 0 0 20px -8px rgba(99, 102, 241, 0.1)",
    "primaryGlow": "0 0 15px rgba(99, 102, 241, 0.15)",
    "button": "0 10px 15px -3px rgba(99, 102, 241, 0.2)"
  },
  "transitions": {
    "default": "all 0.25s ease",
    "pageFadeIn": "fade-in 0.35s cubic-bezier(0.4, 0, 0.2, 1) both"
  }
}
```

---

## 10. AI / Developer Recreation Directive

Give this prompt to another developer or AI when building a new dashboard:

```markdown
Build this dashboard adhering strictly to the Datathon26 "CrimeNexus" visual design identity:

1. Palette & Canvas:
   - Root background: #070b13 with an ambient radial gradient centered at #0d1527.
   - Primary brand accent: Electric Indigo (#6366f1). Secondary: Cyan (#22d3ee). Tertiary: Violet (#a78bfa).
   - Semantic alerts: Emerald (#34d399), Amber (#fbbf24), Red (#f87171).

2. Glassmorphic Cards:
   - Container class: .glass-card with background rgba(15, 23, 42, 0.45), backdrop-filter blur(12px), border 1px solid rgba(30, 41, 59, 0.5), inset highlight inset 0 1px 0 rgba(255, 255, 255, 0.03), and rounded-2xl.
   - Hover: Border changes to rgba(99, 102, 241, 0.2) with a soft indigo shadow glow.

3. Typography & Badges:
   - Font: Inter for text; Monospace for numerical counts, IDs, and timestamps.
   - Page Titles: text-2xl font-black uppercase tracking-tight text-slate-100.
   - Section Headers: Must feature a vertical indigo accent bar (w-1 h-[18px] bg-indigo-500 rounded-sm shrink-0) followed by text-sm font-bold uppercase tracking-wider text-slate-200.
   - Badges/Pills: text-[9px] or text-[10px] font-black uppercase tracking-widest px-2 py-0.5 rounded-full with border and 10-20% background tint.

4. Layout & Navigation:
   - Fixed collapsible sidebar (72px collapsed, 256px expanded) with active item highlight bg-indigo-600/10 text-indigo-400 border-indigo-500/20.
   - Sticky 56px top navbar with live green pulsing beacon and breadcrumbs.
   - Page layout: 4-column KPI cards on top, 60/40 chart grid in the middle, and a full-width high-contrast data table at the bottom.
   - Background depth: Add ambient blurred lighting orbs (w-[400px] h-[400px] bg-indigo-500/5 blur-[120px] pointer-events-none).
```
