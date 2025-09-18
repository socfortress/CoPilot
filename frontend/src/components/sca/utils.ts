import { ScaComplianceLevel } from "@/types/sca.d"

export function getComplianceLevel(score: number): ScaComplianceLevel {
	if (score >= 90) return ScaComplianceLevel.Excellent
	if (score >= 80) return ScaComplianceLevel.Good
	if (score >= 70) return ScaComplianceLevel.Average
	if (score >= 60) return ScaComplianceLevel.Poor
	return ScaComplianceLevel.Critical
}
