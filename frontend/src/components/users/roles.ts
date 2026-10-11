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

export function roleTagType(roleName: string | null | undefined): TagProps["type"] {
	switch (roleName?.toLowerCase()) {
		case "admin":
			return "error"
		case "responder":
			return "primary"
		case "analyst":
			return "warning"
		case "scheduler":
			return "info"
		case "customer_user":
			return "success"
		default:
			return "default"
	}
}
