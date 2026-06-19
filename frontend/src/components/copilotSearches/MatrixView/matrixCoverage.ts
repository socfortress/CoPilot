import type { MitreSubTechnique, MitreTechnique } from "@/types/copilotSearches"

export const MATRIX_RULE_POPOVER = {
	trigger: "hover" as const,
	delay: 350,
	duration: 80,
	showArrow: false,
	placement: "right" as const
}

export const MATRIX_RULE_TAG_CLASS =
	"flex cursor-help! items-center px-1! font-mono text-[11px]! [&_.n-tag__content]:flex [&_.n-tag__content]:items-center max-h-5"

export function coverageClass(count: number): string {
	if (count === 0) return "cov-empty"
	if (count === 1) return "cov-1"
	if (count <= 3) return "cov-2"
	if (count <= 7) return "cov-3"
	return "cov-4"
}

export function techniqueCellTooltip(tech: MitreTechnique): string {
	if (tech.total_rule_count === 0) return `${tech.id} ${tech.name} — no CoPilot rules`
	const subDelta = tech.total_rule_count - tech.rule_count
	return subDelta
		? `${tech.id} ${tech.name} — ${tech.rule_count} direct, +${subDelta} via sub-techniques`
		: `${tech.id} ${tech.name} — ${tech.rule_count} rule(s)`
}

export function subTechniqueCellTooltip(sub: MitreSubTechnique): string {
	return sub.rule_count ? `${sub.id} ${sub.name} — ${sub.rule_count} rule(s)` : `${sub.id} ${sub.name} — no rules`
}
