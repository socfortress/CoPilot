import type { TagProps } from "naive-ui"
import { AuthUserRole } from "@/types/auth"

/**
 * What a role means for a user's customers (#1219), mirrored from the backend's
 * customer_assignment rules, which are what enforce them:
 *
 * - analysts and responders see exactly the customers assigned to them, so they are
 *   never created or left without one;
 * - admins see every customer, so assigning them customers means nothing and is not offered.
 */

export const ROLE_NAME_OPTIONS = [
	{ label: "Admin", value: "admin" },
	{ label: "Analyst", value: "analyst" },
	{ label: "Responder", value: "responder" },
	{ label: "Scheduler", value: "scheduler" },
	{ label: "Customer User", value: "customer_user" }
]

const CUSTOMER_SCOPED = new Set<string | number>(["analyst", "responder", AuthUserRole.Analyst, AuthUserRole.Responder])

export const NEEDS_A_CUSTOMER = "Analysts and responders see only the customers assigned to them: assign at least one."

/** The role (by name or id) sees only its assigned customers, and must have at least one. */
export function needsCustomers(role: string | number | null | undefined): boolean {
	return role != null && CUSTOMER_SCOPED.has(typeof role === "string" ? role.toLowerCase() : role)
}

/** The role sees every customer whatever is assigned. */
export function seesEveryCustomer(role: string | number | null | undefined): boolean {
	return role === AuthUserRole.Admin || (typeof role === "string" && role.toLowerCase() === "admin")
}

/** The role's API name (`customer_user`) from its id. */
export function roleNameOf(role: AuthUserRole | null | undefined): string {
	const key = role ? AuthUserRole[role] : undefined
	return key ? key.replace(/([a-z])([A-Z])/g, "$1_$2").toLowerCase() : ""
}

/** The role's display label ("Customer User"), as the role pickers show it. */
export function roleLabel(roleName: string | null | undefined): string {
	return ROLE_NAME_OPTIONS.find(option => option.value === roleName?.toLowerCase())?.label ?? roleName ?? ""
}

/** The role's icon, written out in full so the icon scan finds it. */
export function roleIcon(roleName: string | null | undefined): string {
	switch (roleName?.toLowerCase()) {
		case "admin":
			return "carbon:user-admin"
		case "responder":
			return "carbon:flash"
		case "analyst":
			return "carbon:search"
		case "scheduler":
			return "carbon:time"
		default:
			return "carbon:user"
	}
}

/**
 * The role's colour: three SOC roles told apart at a glance (Analyst and Responder used to
 * be warning and primary, two yellows).
 */
export function roleTagType(roleName: string | null | undefined): TagProps["type"] {
	switch (roleName?.toLowerCase()) {
		case "admin":
			return "error"
		case "responder":
			return "primary"
		case "analyst":
			return "info"
		case "customer_user":
			return "success"
		default:
			return "default"
	}
}

const TAG_TYPE_COLOR: Record<string, string> = {
	error: "var(--error-color)",
	primary: "var(--primary-color)",
	info: "var(--info-color)",
	success: "var(--success-color)",
	warning: "var(--warning-color)"
}

/** The role's colour as a CSS value, for a dot or a ring beside its name. */
export function roleColor(roleName: string | null | undefined): string {
	return TAG_TYPE_COLOR[roleTagType(roleName) ?? "default"] ?? "var(--fg-tertiary-color)"
}

/** What the role may do, in one line, for the profile. */
export function roleDescription(roleName: string | null | undefined): string {
	switch (roleName?.toLowerCase()) {
		case "admin":
			return "Sees every customer and administers users, connectors and settings."
		case "responder":
			return "An analyst who can also act on the endpoints of the customers assigned to them."
		case "analyst":
			return "Investigates the alerts and cases of the customers assigned to them."
		case "scheduler":
			return "Runs CoPilot's scheduled jobs."
		case "customer_user":
			return "Uses the Customer Portal."
		default:
			return ""
	}
}
