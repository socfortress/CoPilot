import type { NotificationTrigger } from "@/types/notifications"

// The variables a notification template can reference, mirroring
// `build_context` in app/notifications/services/rendering.py.
//
// Kept as data rather than prose so the editor can show exactly what's
// available for the trigger being written against — a list that's wrong is
// worse than no list, because the operator finds out at send time when the
// route silently falls back to the channel default.

export interface TemplateVariable {
	name: string
	description: string
	// Shown in the editor's reference so the operator can see the shape without
	// running a preview.
	example?: string
}

// Available on every event regardless of trigger. These are a fixed contract:
// a typo in one is an error at render time, not an empty string.
export const COMMON_VARIABLES: TemplateVariable[] = [
	{ name: "severity", description: "Critical / High / Medium / Low / Informational", example: "High" },
	{
		name: "customer_code",
		description: "The customer this event belongs to. Empty on internal routes.",
		example: "ACME"
	},
	{ name: "summary", description: "The event's body text — the AI summary, or the alert's description." },
	{ name: "subject", description: "One-line title for the event." },
	{ name: "link_url", description: "Deep link into CoPilot. May be empty.", example: "https://…/alerts/4821" },
	{ name: "entity_type", description: "alert, case or case_task." },
	{ name: "entity_id", description: "Numeric id of that entity.", example: "4821" },
	{ name: "trigger", description: "Which trigger fired this.", example: "alert_created" },
	{
		name: "context.…",
		description:
			"Free-form per-event extras. A missing key renders empty rather than failing, because the same trigger " +
			"carries different keys on different events.",
		example: "context.asset_name"
	},
	{
		name: "branding.…",
		description:
			"The customer's logo and brand colours, resolved the same way a PDF report's are. Keys: logo, title, " +
			"accent, accent_strong, accent_text.",
		example: "branding.accent_strong"
	}
]

// Aliases kept from before templates were Jinja, so anything written against
// the old string-substitution renderer keeps working.
export const LEGACY_ALIASES: TemplateVariable[] = [
	{ name: "alert_id", description: "Alias for entity_id." },
	{ name: "alert_name", description: "The alert's name, falling back to subject." },
	{ name: "report_url", description: "Alias for link_url." }
]

// Only populated on the assignment triggers. Offered elsewhere too — they
// render empty rather than failing — but listing them under a trigger that
// never sets them would invite templates that always have a hole in them.
export const ASSIGNMENT_VARIABLES: TemplateVariable[] = [
	{ name: "assignee", description: "Who it was assigned to.", example: "jdoe" },
	{ name: "actor", description: "Who did the assigning.", example: "asmith" },
	{ name: "context.title", description: "Title of the alert, case or task." }
]

const ALERT_VARIABLES: TemplateVariable[] = [
	{ name: "context.asset_name", description: "Host the alert fired on.", example: "WKSTN-014" },
	{ name: "context.rule_level", description: "Wazuh rule level, when the source provides one.", example: "12" },
	{ name: "context.iocs", description: "Indicators extracted by the investigation. Loop over it — often absent." }
]

// The AI investigation report. Resolved only when a template mentions
// `ai_report`, so listing it here is also what tells an operator the cost is
// opt-in. Absent on most alerts — every example guards accordingly.
const AI_REPORT_VARIABLES: TemplateVariable[] = [
	{
		name: "context.ai_report.html",
		description: "The full report rendered as HTML, tables included. Use in an html-format template; email only.",
		example: "{% if context.ai_report %}{{ context.ai_report.html }}{% endif %}"
	},
	{ name: "context.ai_report.markdown", description: "The raw markdown source of the report." },
	{ name: "context.ai_report.summary", description: "The report's short summary." },
	{ name: "context.ai_report.recommended_actions", description: "The AI's suggested next steps." },
	{
		name: "context.ai_report.severity",
		description: "The AI's assessment of the finding — often lower than the alert's own severity.",
		example: "Medium"
	},
	{
		name: "context.ai_report.iocs",
		description: "Indicators with verdicts. Each has .value, .type, .vt_verdict and .vt_score.",
		example: "{% for i in context.ai_report.iocs %}{{ i.value }} ({{ i.vt_verdict }}){% endfor %}"
	}
]

// Set only by the analyst sign-off trigger.
const REVIEW_VARIABLES: TemplateVariable[] = [
	{ name: "context.reviewer", description: "Username of the analyst who signed off.", example: "asmith" },
	{ name: "context.verdict", description: "Their overall verdict, when they gave one.", example: "up" },
	{ name: "context.report_id", description: "Id of the report that was reviewed." }
]

// The temporary-password email (#999). These are top-level extras supplied by
// `build_extra_context` in app/auth/services/temp_password_email.py, not event
// fields — which is why none of them lives under `context.`.
//
// This trigger's list is EXCLUSIVE rather than additive: an alert variable has
// no meaning in a password email, and `severity` would render "Informational"
// at a recipient who is not being told about a finding at all.
const TEMP_PASSWORD_VARIABLES: TemplateVariable[] = [
	{ name: "user_name", description: "Username of the account the password was issued for.", example: "jdoe" },
	{ name: "user_email", description: "Address the email is being sent to.", example: "jdoe@example.com" },
	{
		name: "temp_password",
		description: "The temporary password itself. A template that omits it sends the user nothing usable.",
		example: "Xk4mR-9pLzAq2Vth"
	},
	{
		name: "login_url",
		description: "Sign-in URL, built from COPILOT_URL. Empty when that is unset — guard it with {% if %}.",
		example: "https://copilot.example.com/login"
	},
	{
		name: "customer_name",
		description: "The customer's display name, falling back to their code. Empty for a user scoped to several.",
		example: "Acme Corp"
	},
	{ name: "organization_name", description: "Alias for customer_name." },
	{
		name: "branding.…",
		description:
			"The customer's logo and brand colours, resolved the same way a PDF report's are. Keys: logo, title, " +
			"accent, accent_strong, accent_soft, accent_text.",
		example: "branding.accent_strong"
	}
]

const ASSIGNMENT_TRIGGERS: NotificationTrigger[] = ["alert_assigned", "case_assigned", "case_task_assigned"]

/** Variables worth showing for a given trigger, most relevant first. */
export function variablesForTrigger(trigger: NotificationTrigger | null): TemplateVariable[] {
	// Returned early and alone: this trigger shares the table and the renderer
	// with notifications but none of their variables, so appending the common
	// set would advertise `summary` and `link_url` as usable when they carry
	// alert-shaped placeholder text nobody wants in a credentials email.
	if (trigger === "temp_password_issued") return TEMP_PASSWORD_VARIABLES

	// The report rides alert-shaped events: investigation_complete carries one,
	// and a manual send can attach one to any alert. Assignment triggers never
	// do, so listing it there would invite a template with a permanent hole.
	const specific = !trigger
		? [...ASSIGNMENT_VARIABLES, ...ALERT_VARIABLES, ...AI_REPORT_VARIABLES, ...REVIEW_VARIABLES]
		: ASSIGNMENT_TRIGGERS.includes(trigger)
			? ASSIGNMENT_VARIABLES
			: trigger === "ai_report_reviewed"
				? [...REVIEW_VARIABLES, ...ALERT_VARIABLES, ...AI_REPORT_VARIABLES]
				: [...ALERT_VARIABLES, ...AI_REPORT_VARIABLES]

	return [...specific, ...COMMON_VARIABLES, ...LEGACY_ALIASES]
}

// Small worked examples, so the first thing an operator sees isn't a blank box.
// Each one is valid against every trigger.
export const SNIPPETS: { label: string; source: string }[] = [
	{
		label: "Conditional",
		source: "{% if context.asset_name %}Asset: {{ context.asset_name }}{% endif %}"
	},
	{
		label: "Loop over IOCs",
		source: "{% for ioc in context.iocs %}• {{ ioc.value }} ({{ ioc.type }})\n{% endfor %}"
	},
	{
		label: "Fallback value",
		source: "{{ assignee or 'unassigned' }}"
	},
	{
		label: "Uppercase filter",
		source: "{{ severity | upper }}"
	},
	{
		label: "Link, when there is one",
		source: "{% if link_url %}Open in CoPilot: {{ link_url }}{% endif %}"
	},
	{
		label: "AI report, or the summary",
		source: "{% if context.ai_report %}{{ context.ai_report.html }}{% else %}{{ summary }}{% endif %}"
	}
]

// The password email's own snippets. Offering the alert ones here would put
// `context.iocs` in front of someone writing a credentials email — every one of
// them renders empty, and finding that out costs a real send.
export const TEMP_PASSWORD_SNIPPETS: { label: string; source: string }[] = [
	{
		label: "Greeting",
		source: "Hello {{ user_name }},"
	},
	{
		label: "The password",
		source: "Temporary password: {{ temp_password }}"
	},
	{
		label: "Sign-in link, when configured",
		source: "{% if login_url %}Sign in: {{ login_url }}{% endif %}"
	},
	{
		label: "Organization name, with fallback",
		source: "{{ customer_name or 'CoPilot' }}"
	},
	{
		label: "Brand colour",
		source: '<span style="color:{{ branding.accent_strong }}">…</span>'
	}
]

/** Snippets worth offering for a given trigger. */
export function snippetsForTrigger(trigger: NotificationTrigger | null): { label: string; source: string }[] {
	return trigger === "temp_password_issued" ? TEMP_PASSWORD_SNIPPETS : SNIPPETS
}
