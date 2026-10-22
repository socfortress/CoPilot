import type { TenantUser } from "@/types/users"

/** A portal user as the Users page receives them (#1296). */
export function tenantUser(id: number, username: string, extra: Partial<TenantUser> = {}): TenantUser {
	return {
		id,
		username,
		email: `${username}@acme.example`,
		customers: [{ customer_code: "ACME", customer_name: "Acme", is_customer_admin: false }],
		is_customer_admin: false,
		disabled: false,
		disabled_at: null,
		must_change_password: false,
		totp_enabled: false,
		last_login_at: null,
		is_self: false,
		can_manage: true,
		managed_by_soc_reason: null,
		...extra
	}
}
