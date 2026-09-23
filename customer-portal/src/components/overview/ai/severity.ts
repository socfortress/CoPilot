import type { StatusSegment } from "../shared/status"
import { severityColor } from "../shared/status"

/** Display order; anything else the backend reports (e.g. "Unknown") goes last. */
const SEVERITY_ORDER = ["Critical", "High", "Medium", "Low", "Informational"]
const ATTENTION_SEVERITIES = new Set(["critical", "high"])

function rank(severity: string) {
	const index = SEVERITY_ORDER.indexOf(severity)
	return index === -1 ? SEVERITY_ORDER.length : index
}

/** Latest-report severity counts → ordered, coloured segments (empty buckets dropped). */
export function severitySegments(counts: Record<string, number>): StatusSegment[] {
	return Object.entries(counts)
		.filter(([, count]) => count > 0)
		.sort(([a], [b]) => rank(a) - rank(b))
		.map(([severity, count]) => ({
			key: severity,
			label: severity.toLowerCase(),
			value: count,
			color: severityColor(severity)
		}))
}

/** How many analyzed alerts came out high or critical — the number worth a headline. */
export function attentionCount(segments: StatusSegment[]): number {
	return segments
		.filter(segment => ATTENTION_SEVERITIES.has(segment.key.toLowerCase()))
		.reduce((sum, segment) => sum + segment.value, 0)
}
