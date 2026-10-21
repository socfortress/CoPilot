import type { TalonAutomationLevel, TalonAutomationMode } from "@/api/endpoints/talonAutomation"

/** What each level may run (talon-analyst D85). */
export const LEVEL_TEXT: Record<TalonAutomationLevel, { title: string; detail: string }> = {
	1: {
		title: "Read-only collections",
		detail: "Auto-run catalogue collections on the alert's own host: processes, network connections, services, scheduled tasks and startup items. They write nothing on the endpoint."
	},
	2: {
		title: "Wider collections and files",
		detail: "Catalogue artifacts an admin chooses, and single files under path rules. Collected files stay in CoPilot; the AI Analyst sees only their metadata and hash, never the contents."
	},
	3: {
		title: "Read-only commands",
		detail: "PowerShell or bash commands that CoPilot's copy of the command filter labels read-only, without file readers or environment dumps."
	},
	4: {
		title: "Free-form commands",
		detail: "Any command the filter accepts. A command with a risk label (delete or kill, registry or service, account change, persistence, shutdown, network fetch) never runs on auto."
	}
}

export const MODE_TEXT: Record<TalonAutomationMode, { label: string; detail: string }> = {
	off: { label: "Off", detail: "Nothing at this level runs or is recorded." },
	shadow: {
		label: "Shadow",
		detail: "Would-have-run: every check runs and the exact request is recorded, but nothing runs on the host."
	},
	propose: {
		label: "Propose",
		detail: "The investigation records an approval card for an analyst and never waits. Until investigation proposals are built, it is recorded as shadow."
	},
	auto: {
		label: "Auto",
		detail: "Runs on the alert's own host as the Talon service user, within the caps, with every check in CoPilot."
	}
}

/**
 * Readable labels for the caps CoPilot reports. The names, defaults and values always come from the
 * response (`cap_defaults`, `effective_caps`, `caps`); a name not listed here shows as itself.
 */
export const CAP_LABELS: Record<string, string> = {
	per_alert: "Level 1 collections per alert (per 2 hours)",
	per_host_hour: "Automated starts per host per hour",
	per_customer_hour: "Collections per customer per hour (levels 1–2)",
	level_2_artifacts_per_alert: "Level 2 artifacts per alert",
	files_per_alert: "Files per alert",
	files_per_customer_day: "Files per customer per day",
	file_bytes_per_customer_day: "File bytes per customer per day",
	commands_per_alert: "Commands per alert",
	free_form_per_alert: "Free-form commands per alert",
	commands_per_customer_day: "Commands per customer per day"
}

export function capLabel(name: string): string {
	return CAP_LABELS[name] ?? name
}
