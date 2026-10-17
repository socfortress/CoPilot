// The Budgets tab's form rules (talon-analyst FR-COST-4 "API"; CoPilot `services/talon_usage.py`).
//
// A window is "the default" (null: the `TALON_BUDGET_*` setting applies), "unlimited", or an amount:
// a positive decimal string of at most 12 places and at most $1,000,000,000, exactly what CoPilot's
// `USD_AMOUNT` and `MAX_BUDGET_USD` accept. Checked as text, never as a float, and sent as typed
// (trimmed): `12.50` stays `12.50`.
import type { TalonBudgetAmount, TalonBudgetEntry, TalonBudgetUpdate } from "@/types/talonUsage"

/** CoPilot `talon_usage.USD_AMOUNT`. */
export const BUDGET_AMOUNT = /^(?:0|[1-9]\d{0,9})(?:\.\d{1,12})?$/
/** CoPilot `talon_usage.MAX_BUDGET_USD`, as text. */
export const MAX_BUDGET_USD = "1000000000"
export const UNLIMITED = "unlimited"

export type BudgetChoice = "default" | "unlimited" | "amount"

export interface BudgetWindowForm {
	choice: BudgetChoice
	amount: string
}

export const SOURCE_LABELS: Record<string, string> = {
	default: "Default",
	override: "Override",
	unlimited: "Unlimited",
	unset: "Not set"
}

/** What is wrong with an amount as typed, or null when CoPilot would take it. */
export function budgetAmountProblem(text: string): string | null {
	const amount = text.trim()
	if (!amount) return "Enter an amount."
	if (!BUDGET_AMOUNT.test(amount)) return "A positive amount in USD, such as 25 or 12.50 (at most 12 decimal places)."
	const [whole, fraction = ""] = amount.split(".")
	if (/^0$/.test(whole) && /^0*$/.test(fraction)) return "The amount must be more than 0."
	const over =
		whole.length > MAX_BUDGET_USD.length ||
		(whole.length === MAX_BUDGET_USD.length &&
			(whole > MAX_BUDGET_USD || (whole === MAX_BUDGET_USD && /[1-9]/.test(fraction))))
	if (over) return `At most ${MAX_BUDGET_USD} USD.`
	return null
}

export function windowProblem(form: BudgetWindowForm): string | null {
	return form.choice === "amount" ? budgetAmountProblem(form.amount) : null
}

/** The form a window opens with, from what it is now. */
export function windowFormFromEntry(entry: TalonBudgetEntry | null | undefined): BudgetWindowForm {
	if (entry?.source === "override" && entry.limit_usd) return { choice: "amount", amount: entry.limit_usd }
	if (entry?.source === "unlimited") return { choice: "unlimited", amount: "" }
	return { choice: "default", amount: "" }
}

export function windowValue(form: BudgetWindowForm): TalonBudgetAmount {
	if (form.choice === "unlimited") return UNLIMITED
	if (form.choice === "amount") return form.amount.trim()
	return null
}

/** The PUT body: both windows, always (the PUT replaces both). */
export function budgetPayload(daily: BudgetWindowForm, monthly: BudgetWindowForm): TalonBudgetUpdate {
	return { daily_usd: windowValue(daily), monthly_usd: windowValue(monthly) }
}

/** A window's choice in words, for the confirmation. */
export function describeWindow(form: BudgetWindowForm): string {
	if (form.choice === "unlimited") return "unlimited"
	if (form.choice === "amount") return `$${form.amount.trim()}`
	return "the default"
}

/** A ceiling as the table shows it: the API's string, or what no ceiling means. */
export function limitText(entry: TalonBudgetEntry): string {
	if (entry.limit_usd !== null) return `$${entry.limit_usd}`
	return entry.source === "unlimited" ? "Unlimited" : "No limit"
}
