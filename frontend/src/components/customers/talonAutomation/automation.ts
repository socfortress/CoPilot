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
 * The honest risk of levels 3–4 (plan AUTOMATION-POLICY.md, "The honest risk"; D85's accepted
 * residual risks). Shown before a raise is saved; the admin's acknowledgement is recorded.
 */
export const HONEST_RISK_TEXT = [
	"At levels 3 and 4 on auto, anyone who can write text into this customer's logs can try to steer a command onto that host.",
	"Talon downgrades a command that repeats alert text, or that comes after data the prompt-injection defender flagged, and CoPilot never runs a risk-labelled command on auto. These checks are not a boundary: a paraphrased or self-composed command copies nothing, a command under 8 characters (such as whoami or netstat) never trips the copy check, and an instruction the defender doesn't flag leaves the run unflagged.",
	"Levels 3 and 4 are off by default. Raising one records your name, the time, the old and new values and this acknowledgement in CoPilot's audit."
] as const

/** Labels for the caps CoPilot reports (Q9). An unknown key shows as itself. */
export const CAP_LABELS: Record<string, { label: string; unit: string }> = {
	per_alert_level_1: { label: "Level 1 collections per alert", unit: "per 2 hours" },
	per_alert_level_2_artifacts: { label: "Level 2 artifacts per alert", unit: "per 2 hours" },
	per_alert_level_2_files: { label: "Level 2 files per alert", unit: "per 2 hours" },
	per_alert_commands: { label: "Commands per alert", unit: "per 2 hours" },
	per_alert_free_form: { label: "Free-form commands per alert", unit: "per 2 hours" },
	per_host_hour: { label: "Automated starts per host", unit: "per hour" },
	per_customer_collections_hour: { label: "Collections (levels 1–2)", unit: "per hour" },
	per_customer_files_day: { label: "Files", unit: "per day" },
	per_customer_file_mb_day: { label: "File volume (MB)", unit: "per day" },
	per_customer_commands_day: { label: "Commands", unit: "per day" }
}

export function capLabel(key: string): { label: string; unit: string } {
	return CAP_LABELS[key] ?? { label: key, unit: "" }
}
