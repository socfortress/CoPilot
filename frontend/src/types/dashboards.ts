export type DashboardPanelType = "stat" | "pie" | "bar_h" | "histogram" | "table"

export interface DashboardPanel {
	id: string
	title: string
	type: DashboardPanelType
	w: number
	h: number
	lucene: string
	/** Aggregation field, for `pie` / `bar_h` panels. */
	field?: string
	/** Source fields projected by `table` panels. */
	fields?: string[]
	size?: number
}

export interface DashboardTemplate {
	id: string
	title: string
	description: string
	panels: DashboardPanel[]
}

export interface DashboardCategory {
	id: string
	title: string
	description: string
	vendor: string
	product: string
	event_type: string
	tags: string[]
	color: string
	icon: string
}

export interface DashboardCategoryWithTemplates extends DashboardCategory {
	templates: DashboardTemplate[]
}

export interface EnabledDashboard {
	id: number
	customer_code: string
	event_source_id: number
	library_card: string
	template_id: string
	display_name: string
	created_at: string
}

export interface EnableDashboardPayload {
	customer_code: string
	event_source_id: number
	library_card: string
	template_id: string
	display_name: string
}

export interface PanelResult {
	type: string
	value: number | null
	labels: string[]
	data: number[]
	/** `table` panels only: column keys, in display order. */
	columns?: string[] | null
	/** `table` panels only: one object per document, keyed by column. */
	rows?: Record<string, string | number | boolean | null>[] | null
	error: string | null
}

export interface PanelDataResponse {
	panels: Record<string, PanelResult>
	template: DashboardTemplate
	dashboard_id: number
	customer_code: string
	source_name: string
	accent_color: string
}

// ── Custom dashboards (UI-authored, DB-backed templates) ─────────

/** Reserved `library_card` value used by every dashboard enabled from a custom template. */
export const CUSTOM_LIBRARY_CARD = "custom"

/** Panel as edited in the builder: the id is assigned by the backend when omitted. */
export interface CustomDashboardPanel extends Omit<DashboardPanel, "id"> {
	id?: string
}

/** Portable dashboard definition — the shape of an exported/imported JSON file. */
export interface CustomDashboardDefinition {
	template_key?: string | null
	title: string
	description: string
	vendor: string
	product: string
	event_type: string
	tags: string[]
	color: string
	icon: string
	default_query: string
	panels: CustomDashboardPanel[]
}

export interface CustomDashboard extends Omit<CustomDashboardDefinition, "template_key" | "panels"> {
	id: number
	template_key: string
	customer_code: string | null
	panels: DashboardPanel[]
	created_by: string | null
	created_at: string
	updated_at: string
}

export interface CustomDashboardCreatePayload extends CustomDashboardDefinition {
	customer_code?: string | null
}

export interface CustomDashboardUpdatePayload extends Partial<CustomDashboardDefinition> {
	customer_code?: string | null
	/** Explicit flag: a null `customer_code` can't express "share with everyone" in a partial update. */
	share_globally?: boolean
}

export interface CustomDashboardImportPayload {
	definition: CustomDashboardDefinition
	customer_code?: string | null
	overwrite?: boolean
}

export interface CustomDashboardPreviewPayload {
	event_source_id: number
	default_query: string
	panels: CustomDashboardPanel[]
	timerange: string
}

export interface CustomDashboardPreviewResponse {
	panels: Record<string, PanelResult>
	template: DashboardTemplate
	customer_code: string
	source_name: string
}
