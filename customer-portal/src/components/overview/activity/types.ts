import type { StatusColor } from "../shared/status"

/** One row of an Overview feed, whatever it represents (alert, case, AI finding). */
export interface ActivityItem {
	id: number
	title: string
	/** Shown under the title only when it adds something (alerts often repeat their name here). */
	detail?: string
	detailLines?: 1 | 2
	/** Workflow status or severity: drives the status rail and the leading label of the meta line. */
	status: { label: string; color: StatusColor }
	time: string | Date
	/** Short facts shown after the status, joined with " · " (source, asset, assignee…). */
	meta: string[]
}

/** The shape a placeholder row takes, so it occupies the same space as a real one. */
export interface ActivitySkeletonShape {
	detailLines: number
	titleWidth: string
	metaWidth: string
}
