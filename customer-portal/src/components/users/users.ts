import type { TenantUser } from "@/types/users"
import { i18nGlobal } from "@/lang"

/**
 * Pure logic of the Users page (#1296): what an invitation must satisfy before it is sent (the
 * API's own rules, so the form never accepts what it refuses) and how a user's state reads. Its
 * texts are translated when they are asked for (#1310), so they follow a language change.
 */

/** The API's username rule (`schema/tenant_users.py:USERNAME_PATTERN`), worded in `users.invite.problems.usernameInvalid`. */
export const USERNAME_PATTERN = /^[A-Z0-9][\w.@-]{2,63}$/i
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
	const t = i18nGlobal.t
	if (!username) problems.username = t("users.invite.problems.usernameRequired")
	else if (!USERNAME_PATTERN.test(username)) problems.username = t("users.invite.problems.usernameInvalid")
	const email = form.email.trim()
	if (!email) problems.email = t("users.invite.problems.emailRequired")
	else if (!EMAIL_PATTERN.test(email)) problems.email = t("users.invite.problems.emailInvalid")
	if (!form.customerCodes.length) problems.customerCodes = t("users.invite.problems.customersRequired")
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
	const t = i18nGlobal.t
	const tags: StatusTag[] = []
	if (user.is_self) {
		tags.push({ key: "self", label: t("users.tags.self"), type: "default", title: t("users.tags.selfTitle") })
	}
	if (user.is_customer_admin) {
		tags.push({ key: "admin", label: t("users.tags.admin"), type: "info", title: t("users.tags.adminTitle") })
	}
	if (user.disabled) {
		tags.push({
			key: "disabled",
			label: t("users.tags.disabled"),
			type: "error",
			title: t("users.tags.disabledTitle")
		})
	}
	if (user.must_change_password && !user.disabled) {
		tags.push({
			key: "password",
			label: t("users.tags.password"),
			type: "warning",
			title: t("users.tags.passwordTitle")
		})
	}
	return tags
}

/** Users who can't sign in sort last; the API already puts the caller first. */
export function sortUsers(users: TenantUser[]): TenantUser[] {
	return [...users].sort((a, b) => Number(!a.is_self) - Number(!b.is_self) || Number(a.disabled) - Number(b.disabled))
}
