import type { TenantUser } from "@/types/users"

/**
 * Pure logic of the Users page (#1296): what an invitation must satisfy before it is sent (the
 * API's own rules, so the form never accepts what it refuses) and how a user's state reads.
 */

/** The API's username rule (`schema/tenant_users.py:USERNAME_PATTERN`). */
export const USERNAME_PATTERN = /^[A-Z0-9][\w.@-]{2,63}$/i
export const USERNAME_RULE = "3 to 64 characters: letters, digits and . _ @ -, starting with a letter or a digit"
const EMAIL_PATTERN = /^[^\s@]+@[^\s@][^\s.@]*\.[^\s@]+$/

export interface InviteForm {
	username: string
	email: string
	customerCodes: string[]
}

/** What is wrong with an invitation, field by field; empty when it can be sent. */
export function inviteProblems(form: InviteForm): Partial<Record<keyof InviteForm, string>> {
	const problems: Partial<Record<keyof InviteForm, string>> = {}
	const username = form.username.trim()
	if (!username) problems.username = "Enter a username"
	else if (!USERNAME_PATTERN.test(username)) problems.username = `Username must be ${USERNAME_RULE}`
	const email = form.email.trim()
	if (!email) problems.email = "Enter an email address"
	else if (!EMAIL_PATTERN.test(email)) problems.email = "Enter a valid email address"
	if (!form.customerCodes.length) problems.customerCodes = "Choose at least one customer"
	return problems
}

export type TagType = "default" | "info" | "success" | "warning" | "error"

export interface StatusTag {
	key: string
	label: string
	type: TagType
	title: string
}

/** The tags beside a user's name: what an admin needs to know at a glance, in that order. */
export function statusTags(user: TenantUser): StatusTag[] {
	const tags: StatusTag[] = []
	if (user.is_self) tags.push({ key: "self", label: "You", type: "default", title: "Your own account" })
	if (user.is_customer_admin) {
		tags.push({
			key: "admin",
			label: "Admin",
			type: "info",
			title: "Manages this customer's users. Appointed by your SOC."
		})
	}
	if (user.disabled) {
		tags.push({ key: "disabled", label: "Disabled", type: "error", title: "Cannot sign in" })
	}
	if (user.must_change_password && !user.disabled) {
		tags.push({
			key: "password",
			label: "Password change pending",
			type: "warning",
			title: "Signs in with a temporary password and must choose their own"
		})
	}
	return tags
}

/** Users who can't sign in sort last; the API already puts the caller first. */
export function sortUsers(users: TenantUser[]): TenantUser[] {
	return [...users].sort((a, b) => Number(!a.is_self) - Number(!b.is_self) || Number(a.disabled) - Number(b.disabled))
}
