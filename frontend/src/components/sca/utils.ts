import { ScaComplianceLevel } from "@/types/sca.d"

export function getComplianceLevel(score: number): ScaComplianceLevel {
	if (score >= 90) return ScaComplianceLevel.Excellent
	if (score >= 80) return ScaComplianceLevel.Good
	if (score >= 70) return ScaComplianceLevel.Average
	if (score >= 60) return ScaComplianceLevel.Poor
	return ScaComplianceLevel.Critical
}

export function getComplianceLevelColor(level: ScaComplianceLevel): "primary" | "warning" | "success" | "danger" {
	switch (level) {
		case ScaComplianceLevel.Excellent:
			return "success"
		case ScaComplianceLevel.Good:
			return "primary"
		case ScaComplianceLevel.Average:
			return "warning"
		case ScaComplianceLevel.Poor:
			return "warning"
		case ScaComplianceLevel.Critical:
			return "danger"
		default:
			return "primary"
	}
}

export function getComplianceLevelIcon(level: ScaComplianceLevel): string {
	switch (level) {
		case ScaComplianceLevel.Excellent:
			return "carbon:checkmark-filled"
		case ScaComplianceLevel.Good:
			return "carbon:checkmark"
		case ScaComplianceLevel.Average:
			return "carbon:warning-alt"
		case ScaComplianceLevel.Poor:
			return "carbon:warning"
		case ScaComplianceLevel.Critical:
			return "carbon:warning-filled"
		default:
			return "carbon:help"
	}
}
