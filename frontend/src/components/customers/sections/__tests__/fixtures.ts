import type { CustomerSectionStatus } from "@/types/customers"

/** A customer with some sections on, some off, and lists of every size. */
export function statusFixture(overrides: Partial<CustomerSectionStatus> = {}): CustomerSectionStatus {
	return {
		integrations: { count: 2 },
		network_connectors: { count: 0 },
		event_sources: { count: 1 },
		waf: { count: 3 },
		knowledge: { count: 4 },
		ai_triggers: { on: true },
		notification_workflows: { count: 1 },
		notification_routes: { count: 2 },
		portal_branding: { on: true },
		portal_languages: { on: false, count: 1 },
		portal_sla: { on: true },
		portal_activity: { on: false },
		portal_exposure: { on: false },
		portal_audit: { on: true },
		portal_ai_report: { on: true },
		portal_talon_chat: { on: true },
		portal_ask_soc: { on: true },
		portal_ioc_enrichment: { on: true },
		portal_notifications: { on: true },
		...overrides
	}
}
