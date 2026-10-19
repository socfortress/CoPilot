import type { AiInsights } from "./aiReports"
import type { AlertStatus } from "./alerts"
import type { CaseStatus } from "./cases"

/** The global settings as served publicly: the logo is fetched separately from `logo_url`. */
export interface PortalSettings {
	id: number
	title: string
	/** Versioned logo path relative to the API root, or null when no logo is set. */
	logo_url: string | null
	logo_mime_type: string | null
	brand_color: string | null
	/** Whether the interface takes `brand_color` as its primary color (#1278); the login page reads it here. */
	theme_from_brand_color?: boolean
	updated_at: string | null
}

/**
 * The branding resolved for the authenticated user: their customer's override
 * where one is configured, otherwise the global portal settings. `source` says
 * which one won, so the UI can be reasoned about without diffing values.
 */
export interface EffectivePortalBranding {
	title: string
	/** Versioned logo path relative to the API root; authenticated, so fetch it through the HTTP client. */
	logo_url: string | null
	logo_mime_type: string | null
	brand_color: string | null
	/** Whether the interface takes `brand_color` as its primary color (#1278), as chosen in CoPilot. */
	theme_from_brand_color?: boolean
	source: "custom" | "global"
	customer_code: string | null
}

/** Per-status totals, as `/customer_portal/overview` and the list endpoints report them. */
export interface StatusCounts {
	total: number
	open: number
	in_progress: number
	closed: number
	/** Items the SOC is waiting on the customer for. */
	pending_customer: number
}

export interface AgentCounts {
	total: number
	online: number
	offline: number
	critical: number
}

/** An alert as the Overview shows it: a light projection, not the full `Alert`. */
export interface OverviewAlert {
	id: number
	alert_name: string
	alert_description: string | null
	status: AlertStatus
	alert_creation_time: string
	source: string
	customer_code: string
	asset_names: string[]
}

/** A case as the Overview shows it: a light projection, not the full `Case`. */
export interface OverviewCase {
	id: number
	case_name: string
	case_description: string | null
	case_status: CaseStatus
	case_creation_time: string
	assigned_to: string | null
	customer_code: string | null
	alert_count: number
}

/** `GET /customer_portal/overview`. Each section fails on its own: `error` is set only on the one that did. */
export interface PortalOverview {
	alerts: { counts: StatusCounts; recent: OverviewAlert[]; error: string | null }
	cases: { counts: StatusCounts; recent: OverviewCase[]; error: string | null }
	agents: AgentCounts & { error: string | null }
	ai: AiInsights & { error: string | null }
}

/** One UTC hour of `GET /customer_portal/overview/trend`; hours with nothing are omitted. */
export interface OverviewTrendHour {
	/** ISO 8601, UTC, on the hour: `2026-10-17T09:00:00Z`. */
	hour: string
	alerts_opened: number
	alerts_closed: number
	cases_opened: number
	cases_closed: number
}

export type OverviewTrendRange = "7d" | "30d"

/**
 * Alerts and cases opened and closed per UTC hour, over the range plus one day, so any
 * timezone can sum whole local days out of it. Each entity fails on its own.
 */
export interface OverviewTrend {
	range: OverviewTrendRange
	since: string
	/** The next whole hour: the latest hour counted ends here. */
	until: string
	hours: OverviewTrendHour[]
	/**
	 * Still open at `since`. Each hour's opened − closed added to it gives how many were
	 * open at any later moment: the absolute Net, beside the relative opened − closed.
	 * `null` when that entity failed.
	 */
	alerts_open_at_since: number | null
	cases_open_at_since: number | null
	alerts_error: string | null
	cases_error: string | null
}

export interface DashboardStats {
	total_alerts: number
	total_agents: number
	total_cases: number
}

export interface AlertsStats {
	total: number
	open: number
	in_progress: number
	closed: number
	/** Items the SOC is waiting on the customer for. */
	pending_customer: number
}

export interface CasesStats {
	total: number
	open: number
	in_progress: number
	closed: number
	/** Items the SOC is waiting on the customer for. */
	pending_customer: number
}
