<template>
	<div ref="root" class="customer-sections" data-testid="customer-sections">
		<CustomerSectionsBar
			:groups
			:sections="visible"
			:current
			:status
			:pinned
			@select="open"
			@open-group="openGroup"
			@toggle-pin="togglePin"
		/>

		<div class="sections-body">
			<CustomerSectionsRail
				v-if="currentGroup && (!railHidden || narrow)"
				:group="currentGroup"
				:current
				:status
				@select="open"
				@hide="setRailHidden(true)"
			/>

			<div class="sections-main">
				<div class="sections-toolbar" data-testid="section-toolbar">
					<n-button
						v-if="railHidden && !narrow"
						size="small"
						secondary
						data-testid="rail-show"
						@click="setRailHidden(false)"
					>
						<template #icon><Icon name="carbon:side-panel-open" :size="14" /></template>
						Show sections
					</n-button>
					<div class="flex min-w-0 flex-1 flex-wrap items-center gap-x-2 gap-y-1">
						<span v-for="part of currentPath" :key="part" class="toolbar-path">
							{{ part }}
							<Icon name="carbon:chevron-right" :size="11" />
						</span>
						<span class="truncate text-sm font-semibold">{{ currentSection.label }}</span>
						<button
							type="button"
							class="toolbar-pin"
							:class="{ 'is-pinned': isPinned(current) }"
							:aria-pressed="isPinned(current)"
							:aria-label="isPinned(current) ? `Unpin ${currentSection.label}` : `Pin ${currentSection.label}`"
							:title="isPinned(current) ? 'Unpin this section' : 'Pin this section'"
							data-testid="section-pin"
							@click="togglePin(current)"
						>
							<Icon :name="isPinned(current) ? 'carbon:pin-filled' : 'carbon:pin'" :size="14" />
						</button>
						<span v-if="currentState?.kind === 'switch'" class="toolbar-state" data-testid="section-state">
							<SectionMark :state="currentState" with-word />
						</span>
					</div>
				</div>

				<div class="sections-panes" :style="{ minHeight: 'min(450px, 90vh)' }">
					<section v-if="wasOpened('Info')" v-show="current === 'Info'" v-bind="pane('Info')">
						<CustomerInfo
							v-if="customerInfo"
							v-model:loading="loadingDeleteModel"
							:customer="customerInfo"
							@delete="emit('delete')"
							@submitted="emit('update:customerInfo', $event)"
						/>
					</section>
					<section v-if="wasOpened('Provision')" v-show="current === 'Provision'" v-bind="pane('Provision')">
						<CustomerProvision
							:customer-meta
							:customer-code="customer.customer_code"
							:customer-name="customer.customer_name"
							@delete="emit('update:customerMeta', null)"
							@submitted="emit('update:customerMeta', $event)"
						/>
					</section>
					<section v-if="wasOpened('Security')" v-show="current === 'Security'" v-bind="pane('Security')">
						<CustomerSecurity :customer-code="customer.customer_code" />
					</section>

					<section v-if="wasOpened('Agents')" v-show="current === 'Agents'" v-bind="pane('Agents', 'pr-0!')">
						<n-scrollbar trigger="none" :class="scrollbarClass">
							<CustomerAgents v-if="customerInfo" :customer="customerInfo" />
						</n-scrollbar>
					</section>
					<section
						v-if="wasOpened('Deploy Agent')"
						v-show="current === 'Deploy Agent'"
						v-bind="pane('Deploy Agent', 'overflow-hidden')"
					>
						<CustomerEdrInstall :customer-code="customer.customer_code" />
					</section>
					<section
						v-if="wasOpened('Healthcheck Wazuh')"
						v-show="current === 'Healthcheck Wazuh'"
						v-bind="pane('Healthcheck Wazuh', 'pr-0!')"
					>
						<n-scrollbar trigger="none" :class="scrollbarClass">
							<CustomerHealthcheckList
								v-model:filters="healthcheckFilters"
								source="wazuh"
								:customer-code="customer.customer_code"
							/>
						</n-scrollbar>
					</section>
					<section
						v-if="wasOpened('Healthcheck Velociraptor')"
						v-show="current === 'Healthcheck Velociraptor'"
						v-bind="pane('Healthcheck Velociraptor', 'pr-0!')"
					>
						<n-scrollbar trigger="none" :class="scrollbarClass">
							<CustomerHealthcheckList
								v-model:filters="healthcheckFilters"
								source="velociraptor"
								:customer-code="customer.customer_code"
							/>
						</n-scrollbar>
					</section>
					<section
						v-if="wasOpened('Wazuh Worker') && customerPortainerStackId !== null"
						v-show="current === 'Wazuh Worker'"
						v-bind="pane('Wazuh Worker')"
					>
						<CustomerWazuhWorker :stack-id="customerPortainerStackId" />
					</section>

					<section
						v-if="wasOpened('3rd Party Integrations')"
						v-show="current === '3rd Party Integrations'"
						v-bind="pane('3rd Party Integrations')"
					>
						<CustomerIntegrations
							:customer-code="customer.customer_code"
							:customer-name="customer.customer_name"
						/>
					</section>
					<section
						v-if="wasOpened('Network Connectors')"
						v-show="current === 'Network Connectors'"
						v-bind="pane('Network Connectors')"
					>
						<CustomerNetworkConnectors
							:customer-code="customer.customer_code"
							:customer-name="customer.customer_name"
						/>
					</section>
					<section
						v-if="wasOpened('Event Sources')"
						v-show="current === 'Event Sources'"
						v-bind="pane('Event Sources')"
					>
						<CustomerEventSources :customer-code="customer.customer_code" />
					</section>
					<section v-if="wasOpened('WAF')" v-show="current === 'WAF'" v-bind="pane('WAF')">
						<CustomerWaf :customer-code="customer.customer_code" />
					</section>

					<section v-if="wasOpened('AI Triggers')" v-show="current === 'AI Triggers'" v-bind="pane('AI Triggers')">
						<CustomerAITriggers :customer-code="customer.customer_code" />
					</section>
					<!-- Talon's automation policy (talon-analyst D85, AP-2): admins only, behind "Talon v2" (D54). -->
					<section
						v-if="wasOpened('AI Automation') && showAutomation"
						v-show="current === 'AI Automation'"
						v-bind="pane('AI Automation')"
					>
						<CustomerTalonAutomation :customer-code="customer.customer_code" />
					</section>
					<section
						v-if="wasOpened('Notification Workflows')"
						v-show="current === 'Notification Workflows'"
						v-bind="pane('Notification Workflows')"
					>
						<CustomerNotificationsWorkflows :customer-code="customer.customer_code" />
					</section>
					<section
						v-if="wasOpened('Notifications')"
						v-show="current === 'Notifications'"
						v-bind="pane('Notifications', 'overflow-hidden')"
					>
						<CustomerAiNotifications :customer-code="customer.customer_code" />
					</section>

					<section v-if="wasOpened('Reporting')" v-show="current === 'Reporting'" v-bind="pane('Reporting')">
						<CustomerReporting :customer-code="customer.customer_code" />
					</section>

					<section
						v-if="wasOpened('Portal Branding')"
						v-show="current === 'Portal Branding'"
						v-bind="pane('Portal Branding')"
					>
						<CustomerPortalBranding :customer-code="customer.customer_code" />
					</section>
					<section
						v-if="wasOpened('Portal Languages')"
						v-show="current === 'Portal Languages'"
						v-bind="pane('Portal Languages')"
					>
						<CustomerPortalLanguages :customer-code="customer.customer_code" />
					</section>
					<section v-if="wasOpened('SLA')" v-show="current === 'SLA'" v-bind="pane('SLA')">
						<CustomerPortalSla :customer-code="customer.customer_code" />
					</section>
					<section v-if="wasOpened('Activity')" v-show="current === 'Activity'" v-bind="pane('Activity')">
						<CustomerPortalActivity :customer-code="customer.customer_code" />
					</section>
					<section v-if="wasOpened('Exposure')" v-show="current === 'Exposure'" v-bind="pane('Exposure')">
						<CustomerPortalExposure :customer-code="customer.customer_code" />
					</section>
					<section v-if="wasOpened('Audit Log')" v-show="current === 'Audit Log'" v-bind="pane('Audit Log')">
						<CustomerPortalAudit :customer-code="customer.customer_code" />
					</section>
					<section v-if="wasOpened('AI Report')" v-show="current === 'AI Report'" v-bind="pane('AI Report')">
						<CustomerPortalAiReport :customer-code="customer.customer_code" />
					</section>
					<section v-if="wasOpened('Talon Chat')" v-show="current === 'Talon Chat'" v-bind="pane('Talon Chat')">
						<!-- The AI Report switch as the page last read it: turning it off there reloads the chat. -->
						<CustomerPortalTalonChat
							:customer-code="customer.customer_code"
							:ai-reports-enabled="status?.portal_ai_report.on ?? null"
						/>
					</section>
					<section
						v-if="wasOpened('Ask the SOC')"
						v-show="current === 'Ask the SOC'"
						v-bind="pane('Ask the SOC')"
					>
						<CustomerPortalAskSoc :customer-code="customer.customer_code" />
					</section>
					<section
						v-if="wasOpened('IOC Enrichment')"
						v-show="current === 'IOC Enrichment'"
						v-bind="pane('IOC Enrichment')"
					>
						<CustomerPortalIocEnrichment :customer-code="customer.customer_code" />
					</section>
					<section
						v-if="wasOpened('Portal Notifications')"
						v-show="current === 'Portal Notifications'"
						v-bind="pane('Portal Notifications')"
					>
						<CustomerPortalNotifications :customer-code="customer.customer_code" />
					</section>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { GroupId, SectionId } from "./sections/sections"
import type { Customer, CustomerMeta } from "@/types/customers"
import { useElementSize } from "@vueuse/core"
import { NButton, NScrollbar } from "naive-ui"
import { computed, defineAsyncComponent, inject, ref, useTemplateRef, watch } from "vue"
import { routeLocationKey, routerKey } from "vue-router"
import Icon from "@/components/common/Icon.vue"
import { useCustomerHealthcheckFilters } from "@/composables/useCustomerHealthcheckFilters"
import { useRouteQueryParam } from "@/composables/useNavigation"
import { useTalonV2AvailabilityWhen } from "@/composables/useTalonV2Gate"
import { useAuthStore } from "@/stores/auth"
import CustomerSectionsBar from "./sections/CustomerSectionsBar.vue"
import CustomerSectionsRail from "./sections/CustomerSectionsRail.vue"
import SectionMark from "./sections/SectionMark.vue"
import {
	DEFAULT_SECTION,
	groupViews,
	sectionById,
	sectionPath,
	sectionState,
	tabToSection,
	visibleSections
} from "./sections/sections"
import { useSectionPreferences } from "./sections/useSectionPreferences"
import { useSectionStatus } from "./sections/useSectionStatus"

const props = defineProps<{
	customer: Customer
	customerInfo: Customer | null
	customerMeta: CustomerMeta | null
	customerPortainerStackId: number | null
	loadingDelete?: boolean
	useMaxHeight?: boolean
}>()

const emit = defineEmits<{
	(e: "delete"): void
	(e: "update:customerInfo", value: Customer): void
	(e: "update:customerMeta", value: CustomerMeta | null): void
	(e: "update:loadingDelete", value: boolean): void
}>()

const CustomerInfo = defineAsyncComponent(() => import("./CustomerInfo.vue"))
const CustomerAgents = defineAsyncComponent(() => import("./CustomerAgents.vue"))
const CustomerEdrInstall = defineAsyncComponent(() => import("./CustomerEdrInstall.vue"))
const CustomerProvision = defineAsyncComponent(() => import("./provision/CustomerProvision.vue"))
const CustomerHealthcheckList = defineAsyncComponent(() => import("./healthcheck/CustomerHealthcheckList.vue"))
const CustomerIntegrations = defineAsyncComponent(() => import("./integrations/CustomerIntegrations.vue"))
const CustomerNetworkConnectors = defineAsyncComponent(
	() => import("./networkConnectors/CustomerNetworkConnectors.vue")
)
const CustomerNotificationsWorkflows = defineAsyncComponent(
	() => import("./notifications/CustomerNotificationsWorkflows.vue")
)
const CustomerAITriggers = defineAsyncComponent(() => import("./aiTriggers/CustomerAITriggers.vue"))
const CustomerTalonAutomation = defineAsyncComponent(() => import("./talonAutomation/CustomerTalonAutomation.vue"))
const CustomerAiNotifications = defineAsyncComponent(() => import("./aiNotifications/CustomerAiNotifications.vue"))
const CustomerEventSources = defineAsyncComponent(() => import("./eventSources/CustomerEventSources.vue"))
const CustomerReporting = defineAsyncComponent(() => import("./reporting/CustomerReporting.vue"))
// Same component as the global Customer Portal settings page — scoped to one customer.
const CustomerPortalBranding = defineAsyncComponent(() => import("@/components/customerPortal/Settings.vue"))
// Per-customer switch for the portal's read-only AI Analyst surfaces.
const CustomerPortalAiReport = defineAsyncComponent(() => import("@/components/customerPortal/AiReportSettings.vue"))
// The portal's Talon chat (talon-analyst D97): its own section (#1333), beside the AI Report it needs.
const CustomerPortalTalonChat = defineAsyncComponent(() => import("@/components/customerPortal/PortalChatSettings.vue"))
// Per-customer switch for the portal's read-only SLA page (#1187).
const CustomerPortalSla = defineAsyncComponent(() => import("@/components/customerPortal/SlaSettings.vue"))
// Per-customer switch for the portal's read-only Activity page (#1284).
const CustomerPortalActivity = defineAsyncComponent(() => import("@/components/customerPortal/ActivitySettings.vue"))
const CustomerPortalNotifications = defineAsyncComponent(
	() => import("@/components/customerPortal/NotificationSettings.vue")
)
// Per-customer switch for the portal's read-only Exposure page: vulnerabilities and compliance (#1289).
const CustomerPortalExposure = defineAsyncComponent(() => import("@/components/customerPortal/ExposureSettings.vue"))
// Per-customer switch for the portal's Audit Log page, read by the customer's own administrators (#1298).
const CustomerPortalAudit = defineAsyncComponent(() => import("@/components/customerPortal/AuditSettings.vue"))
const CustomerPortalLanguages = defineAsyncComponent(() => import("@/components/customerPortal/LanguageSettings.vue"))
// Per-customer switch for "Ask the SOC": portal users' questions about their alerts and cases (#1305).
const CustomerPortalAskSoc = defineAsyncComponent(() => import("@/components/customerPortal/AskSocSettings.vue"))
// Per-customer switch for Threat Intel on the IOCs of portal users' alerts (#1318).
const CustomerPortalIocEnrichment = defineAsyncComponent(
	() => import("@/components/customerPortal/IocEnrichmentSettings.vue")
)
// SOCFortress WAFs of this customer (#1165) — config, live views and IP blocking.
const CustomerWaf = defineAsyncComponent(() => import("@/components/customerWaf/CustomerWaf.vue"))
const CustomerSecurity = defineAsyncComponent(() => import("./security/CustomerSecurity.vue"))
const CustomerWazuhWorker = defineAsyncComponent(() => import("./CustomerWazuhWorker.vue"))

const { healthcheckFilters } = useCustomerHealthcheckFilters()

const isAdmin = computed(() => useAuthStore().isAdmin)
// The AI Automation section: an admin's, behind "Talon v2" (D54). No one else asks for availability.
const { available: talonV2Available } = useTalonV2AvailabilityWhen(isAdmin)
const showAutomation = computed(() => isAdmin.value && talonV2Available.value)

const loadingDeleteModel = computed({
	get: () => props.loadingDelete ?? false,
	set: value => emit("update:loadingDelete", value)
})

const scrollbarClass = computed(() => (props.useMaxHeight ? "max-h-117.5 pr-4" : undefined))

// Up to 700 px of its own width (a phone, a narrow modal) the rail becomes a row of the group's
// sections, on top, and can't be hidden. Measured on the component, as its container queries are.
const root = useTemplateRef<HTMLElement>("root")
const { width } = useElementSize(root)
const narrow = computed(() => width.value > 0 && width.value <= 700)

// ── which sections, grouped ─────────────────────────────────────────────────

const visible = computed(() =>
	visibleSections({
		admin: isAdmin.value,
		automation: showAutomation.value,
		wazuhWorker: props.customerPortainerStackId !== null
	})
)
const groups = computed(() => groupViews(visible.value))

// ── which one is open ───────────────────────────────────────────────────────

// What the viewer (or the link) asked for. Kept when it isn't shown yet: the AI Automation
// section appears once Talon v2's availability answers, and a link to it then opens it.
const requested = ref<SectionId>(DEFAULT_SECTION)
const current = computed<SectionId>(() =>
	visible.value.some(section => section.id === requested.value) ? requested.value : DEFAULT_SECTION
)
const currentSection = computed(() => sectionById(current.value))
const currentGroup = computed(() => groups.value.find(group => group.id === currentSection.value.group) ?? null)
const currentPath = computed(() => sectionPath(currentSection.value))

const tabQuery = useRouteQueryParam("tab")
watch(
	tabQuery,
	tab => {
		const section = tabToSection(tab)
		if (section) requested.value = section
	},
	{ immediate: true }
)

// On the customer's own page the open section is in the URL (`?tab=`), so a reload or a shared
// link opens it again. In a modal the page behind it keeps its URL.
const router = inject(routerKey, null)
const route = inject(routeLocationKey, null)

function writeTab(id: SectionId) {
	if (!router || route?.name !== "Customer") return
	const tab = id === DEFAULT_SECTION ? undefined : id
	if ((route.query.tab ?? undefined) === tab) return
	void router.replace({ query: { ...route.query, tab } })
}

const lastInGroup = new Map<GroupId, SectionId>()

function open(id: SectionId) {
	requested.value = id
	writeTab(id)
}

function openGroup(id: GroupId) {
	const group = groups.value.find(item => item.id === id)
	if (!group) return
	const last = lastInGroup.get(id)
	const target = group.sections.find(section => section.id === last) ?? group.sections[0]
	if (target) open(target.id)
}

// Sections mount when first opened and stay mounted, as the tabs did (`show:lazy`): a list keeps
// its filters and scroll when the viewer comes back to it.
const visited = ref(new Set<SectionId>())

watch(
	current,
	id => {
		lastInGroup.set(sectionById(id).group, id)
		if (!visited.value.has(id)) visited.value = new Set([...visited.value, id])
	},
	{ immediate: true }
)

function wasOpened(id: SectionId): boolean {
	return visited.value.has(id)
}

function pane(id: SectionId, extra = "") {
	return {
		"class": ["p-4!", extra],
		"aria-label": sectionById(id).label,
		"data-section": id
	}
}

// ── what each section holds ────────────────────────────────────────────────

const { status, refresh } = useSectionStatus(() => props.customer.customer_code)
const currentState = computed(() => sectionState(currentSection.value, status.value))

// A switch may have moved in the section just left: read the lights again.
watch(current, (_id, previous) => {
	if (previous) void refresh()
})

const { pinned, isPinned, togglePin, railHidden, setRailHidden } = useSectionPreferences()
</script>

<style lang="scss" scoped>
.customer-sections {
	container: customer-sections / inline-size;
	display: flex;
	flex-direction: column;
	height: 100%;
	min-height: 0;

	.sections-body {
		display: flex;
		flex: 1;
		min-height: 0;
	}

	.sections-main {
		display: flex;
		flex-direction: column;
		flex: 1;
		min-width: 0;
	}

	.sections-toolbar {
		display: flex;
		align-items: center;
		gap: 10px;
		min-height: 44px;
		padding: 6px 16px;
		border-bottom: 1px solid var(--border-color);
	}

	.toolbar-path {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		font-family: var(--font-family-mono);
		font-size: 11px;
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: var(--fg-secondary-color);
	}

	// Discreet beside the section's name: the section is the point, pinning it an aside.
	.toolbar-pin {
		display: inline-grid;
		place-items: center;
		width: 24px;
		height: 24px;
		border-radius: var(--border-radius-small);
		color: var(--fg-secondary-color);

		&:hover {
			color: var(--fg-default-color);
			background-color: var(--hover-color);
		}

		&.is-pinned {
			color: var(--primary-color);
		}

		&:focus-visible {
			outline: 2px solid var(--primary-color);
			outline-offset: -2px;
		}
	}

	.toolbar-state {
		display: inline-flex;
		align-items: center;
		height: 22px;
		padding: 0 9px;
		margin-left: 4px;
		border: 1px solid var(--border-color);
		border-radius: 11px;
	}

	@container customer-sections (max-width: 700px) {
		.sections-body {
			flex-direction: column;
		}
	}
}
</style>
