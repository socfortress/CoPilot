import type { ApiError } from "@/types/common"
import type {
	IocEnrichment,
	IocKind,
	IocOverallVerdict,
	IocSource,
	IocSourceResult,
	VirusTotalDetails
} from "@/types/iocEnrichment"
import { i18nGlobal } from "@/lang"

/**
 * Pure logic of the IOCs' Threat Intel (#1318): how a verdict and a source's answer read, and
 * which failure a check met. Texts are translated when they are asked for, so they follow a
 * language change. Every value from a source is shown as text by the components, never as markup.
 */

export type TagType = "default" | "info" | "success" | "warning" | "error"
/** What the verdict pill says: a source's verdict, never checked, or a value never sent anywhere. */
export type VerdictKey = IocOverallVerdict | "unchecked" | "not_sent"

/** A verdict's tag: a colour and an icon, always beside its word (never colour alone). */
export const VERDICT_META: Record<VerdictKey, { type: TagType; icon: string }> = {
	malicious: { type: "error", icon: "carbon:warning-filled" },
	suspicious: { type: "warning", icon: "carbon:warning-alt" },
	known: { type: "info", icon: "carbon:information" },
	clean: { type: "success", icon: "carbon:checkmark-outline" },
	unknown: { type: "default", icon: "carbon:help" },
	not_found: { type: "default", icon: "carbon:search" },
	unchecked: { type: "default", icon: "carbon:time" },
	not_sent: { type: "default", icon: "carbon:locked" }
}

/** The only links shown: a value's page on VirusTotal, which the backend builds. */
const VIRUSTOTAL_GUI = "https://www.virustotal.com/gui/"

export function verdictKey(ioc: Pick<IocEnrichment, "verdict" | "kind">): VerdictKey {
	if (ioc.kind === "internal" || ioc.kind === "invalid") return "not_sent"
	return ioc.verdict ?? "unchecked"
}

export function verdictLabel(verdict: VerdictKey): string {
	return i18nGlobal.t(`iocEnrichment.verdicts.${verdict}`)
}

export function sourceLabel(source: IocSource): string {
	return i18nGlobal.t(`iocEnrichment.sources.${source}`)
}

/** Why an IOC is not looked up anywhere, or null when it may be. */
export function kindNote(kind: IocKind): string | null {
	if (kind === "internal") return i18nGlobal.t("iocEnrichment.kinds.internal")
	if (kind === "invalid") return i18nGlobal.t("iocEnrichment.kinds.invalid")
	return null
}

/** What a source's line says, after its name, when it has no answer to show: why, or what went wrong. */
export function sourceStatusText(result: IocSourceResult): string {
	const t = i18nGlobal.t
	if (result.status === "error") {
		return result.error === "rate_limited" ? t("iocEnrichment.errors.rateLimited") : t("iocEnrichment.errors.unavailable")
	}
	return t(`iocEnrichment.status.${result.status}`)
}

/** A source answered: its answer is shown, with a failed refresh beside it if there was one. */
export function hasAnswer(result: IocSourceResult): boolean {
	return result.status === "found" || result.status === "not_found"
}

/** Whether there is anything to open the details for. */
export function hasDetails(ioc: IocEnrichment): boolean {
	return ioc.sources.some(result => result.status === "found" && (result.virustotal || result.opencti))
}

export function enginesFlagged(details: VirusTotalDetails): number {
	return details.malicious + details.suspicious
}

/** The VirusTotal page to open, only when it is one. */
export function virusTotalLink(link: string | null | undefined): string | null {
	return link && link.startsWith(VIRUSTOTAL_GUI) && !/\s/.test(link) ? link : null
}

/** What a failed check tells the user, by the answer's status: never the server's own text. */
export function checkFailureMessage(err: ApiError): string {
	const t = i18nGlobal.t
	switch (err.response?.status) {
		case 403:
			return t("iocEnrichment.failures.notEnabled")
		case 404:
			return t("iocEnrichment.failures.gone")
		case 409:
			return t("iocEnrichment.failures.running")
		case 429:
			return t("iocEnrichment.failures.limit")
		default:
			return t("iocEnrichment.failures.generic")
	}
}

/** The colour family a verdict is drawn in: the theme's status colours, or a neutral ink. */
export type Tone = "error" | "warning" | "info" | "success" | "neutral"

export function toneOf(verdict: VerdictKey | null | undefined): Tone {
	const type = verdict ? VERDICT_META[verdict].type : "default"
	return type === "default" ? "neutral" : type
}

export interface EngineSegment {
	key: "malicious" | "suspicious" | "harmless" | "undetected"
	tone: Tone
	count: number
	/** Share of every engine that answered, 0–100. */
	percent: number
}

/** VirusTotal's engines as the segments of one bar, worst first; the engines' other answers are left blank. */
export function engineSegments(details: VirusTotalDetails): EngineSegment[] {
	const total = details.engines || 0
	const parts: [EngineSegment["key"], Tone][] = [
		["malicious", "error"],
		["suspicious", "warning"],
		["harmless", "success"],
		["undetected", "neutral"]
	]
	return parts
		.map(([key, tone]) => ({ key, tone, count: details[key], percent: total ? (details[key] / total) * 100 : 0 }))
		.filter(segment => segment.count > 0)
}

/** The IOCs keyed by id, as the alert lists them. */
export function byIocId(iocs: IocEnrichment[]): Record<number, IocEnrichment> {
	return Object.fromEntries(iocs.map(ioc => [ioc.ioc_id, ioc]))
}
