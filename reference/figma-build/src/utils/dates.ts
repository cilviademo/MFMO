// Rule-based federal holiday and effective duty-day computation.
// No hardcoded date tables — all dates are derived from rules so the algorithm
// remains correct for any year in the supported FY2026–FY2126 range.

// ── Helper: nth weekday of a month ────────────────────────────────────────────
// weekday: 0=Sun … 6=Sat. n≥1: nth occurrence; n=-1: last occurrence.
function nthWeekdayOfMonth(year: number, month: number, weekday: number, n: number): Date {
  if (n > 0) {
    const first = new Date(year, month, 1)
    const diff = (weekday - first.getDay() + 7) % 7
    return new Date(year, month, 1 + diff + (n - 1) * 7)
  }
  // Last occurrence
  const last = new Date(year, month + 1, 0)
  const diff = (last.getDay() - weekday + 7) % 7
  return new Date(year, month, last.getDate() - diff)
}

// Saturday → observed Friday; Sunday → observed Monday.
function observed(nominal: Date): Date {
  const dow = nominal.getDay()
  if (dow === 6) return new Date(nominal.getFullYear(), nominal.getMonth(), nominal.getDate() - 1)
  if (dow === 0) return new Date(nominal.getFullYear(), nominal.getMonth(), nominal.getDate() + 1)
  return nominal
}

function federalHolidaysForYear(year: number): Date[] {
  return [
    observed(new Date(year, 0, 1)),          // New Year's Day
    nthWeekdayOfMonth(year, 0, 1, 3),        // MLK Jr — 3rd Mon Jan
    nthWeekdayOfMonth(year, 1, 1, 3),        // Washington's Birthday — 3rd Mon Feb
    nthWeekdayOfMonth(year, 4, 1, -1),       // Memorial Day — last Mon May
    observed(new Date(year, 5, 19)),          // Juneteenth
    observed(new Date(year, 6, 4)),           // Independence Day
    nthWeekdayOfMonth(year, 8, 1, 1),        // Labor Day — 1st Mon Sep
    nthWeekdayOfMonth(year, 9, 1, 2),        // Columbus Day — 2nd Mon Oct
    observed(new Date(year, 10, 11)),         // Veterans Day
    nthWeekdayOfMonth(year, 10, 4, 4),       // Thanksgiving — 4th Thu Nov
    observed(new Date(year, 11, 25)),         // Christmas
  ]
}

export function datesMatch(a: Date, b: Date): boolean {
  return sameDay(a, b)
}

function sameDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  )
}

export function isFederalHoliday(date: Date): boolean {
  // Check surrounding years to catch observed holidays that cross year boundaries
  // (e.g. New Year's on Saturday → observed Dec 31 of prior year)
  const y = date.getFullYear()
  const pool = [
    ...federalHolidaysForYear(y - 1),
    ...federalHolidaysForYear(y),
    ...federalHolidaysForYear(y + 1),
  ]
  return pool.some(h => sameDay(h, date))
}

export function isWeekend(date: Date): boolean {
  return date.getDay() === 0 || date.getDay() === 6
}

export function isNonDuty(date: Date): boolean {
  return isWeekend(date) || isFederalHoliday(date)
}

// Roll forward to the next duty day. If date is already a duty day, returns it.
export function nextDutyDay(date: Date): Date {
  let d = new Date(date.getFullYear(), date.getMonth(), date.getDate())
  while (isNonDuty(d)) {
    d = new Date(d.getFullYear(), d.getMonth(), d.getDate() + 1)
  }
  return d
}

// ── Period dates ──────────────────────────────────────────────────────────────

export interface PeriodDates {
  periodYear: number
  periodMonth: number       // 0-indexed
  periodClose: Date
  nominalInitial: Date
  effectiveInitial: Date
  nominalFinal: Date
  effectiveFinal: Date
  fiscalYear: number        // FY Oct–Sep: Aug 2026 → FY26
  fiscalQuarter: 1 | 2 | 3 | 4
  isQuarterlyPeriod: boolean  // Dec / Mar / Jun / Sep
  isEOYPeriod: boolean        // September
}

// initialDay and finalDay are configuration values (policy: day 5 and day 10).
export function getPeriodDates(
  year: number,
  month: number,   // 0-indexed
  initialDay = 5,
  finalDay = 10,
): PeriodDates {
  const periodClose = new Date(year, month + 1, 0) // last calendar day of month

  const followYear = month === 11 ? year + 1 : year
  const followMonth = month === 11 ? 0 : month + 1

  const nominalInitial = new Date(followYear, followMonth, initialDay)
  const effectiveInitial = nextDutyDay(nominalInitial)
  const nominalFinal = new Date(followYear, followMonth, finalDay)
  const effectiveFinal = nextDutyDay(nominalFinal)

  // FY: Oct (month 9) starts a new fiscal year.
  const fiscalYear = month >= 9 ? year + 1 : year

  // FY quarter within FY (Q1=Oct–Dec, Q2=Jan–Mar, Q3=Apr–Jun, Q4=Jul–Sep).
  const fyMonth = month >= 9 ? month - 9 : month + 3
  const fiscalQuarter = (Math.floor(fyMonth / 3) + 1) as 1 | 2 | 3 | 4

  return {
    periodYear: year,
    periodMonth: month,
    periodClose,
    nominalInitial,
    effectiveInitial,
    nominalFinal,
    effectiveFinal,
    fiscalYear,
    fiscalQuarter,
    isQuarterlyPeriod: [11, 2, 5, 8].includes(month), // Dec/Mar/Jun/Sep
    isEOYPeriod: month === 8,                           // September
  }
}

// ── Formatting ────────────────────────────────────────────────────────────────

const MONTH_SHORT = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
const DAY_SHORT   = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"]

export function formatDate(d: Date): string {
  return `${d.getDate()} ${MONTH_SHORT[d.getMonth()]}`
}

export function formatDateWithDay(d: Date): string {
  return `${DAY_SHORT[d.getDay()]} ${d.getDate()} ${MONTH_SHORT[d.getMonth()]}`
}

// "5 Sep (Tue 8 Sep)" when dates differ; "5 Sep" when they match.
export function suspenseLabel(nominal: Date, effective: Date): string {
  return sameDay(nominal, effective)
    ? formatDate(nominal)
    : `${formatDate(nominal)} (${formatDateWithDay(effective)})`
}

// ── Rolling period selector ───────────────────────────────────────────────────

const MONTH_LONG = [
  "January","February","March","April","May","June",
  "July","August","September","October","November","December",
]

export interface PeriodOption {
  value: string   // "2026-08"
  label: string   // "August 2026"
  year: number
  month: number   // 0-indexed
}

// Generates rolling window: 13 months back through 3 months forward from today.
export function generatePeriodOptions(today: Date = new Date()): PeriodOption[] {
  const options: PeriodOption[] = []
  let cur = new Date(today.getFullYear(), today.getMonth() - 13, 1)
  const end = new Date(today.getFullYear(), today.getMonth() + 3, 1)
  while (cur <= end) {
    const y = cur.getFullYear()
    const m = cur.getMonth()
    options.push({
      value: `${y}-${String(m + 1).padStart(2, "0")}`,
      label: `${MONTH_LONG[m]} ${y}`,
      year: y,
      month: m,
    })
    cur = new Date(y, m + 1, 1)
  }
  return options
}
