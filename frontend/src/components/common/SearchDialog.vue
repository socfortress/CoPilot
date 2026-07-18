<template>
	<n-modal v-model:show="showSearchBox" class="search-box-modal">
		<n-card content-class="p-0!" class="w-150!" :bordered="false" size="huge" role="dialog" aria-modal="true">
			<div class="search-box" @keydown.up="prevItem()" @keydown.down="nextItem()">
				<div class="search-input flex items-center">
					<Icon :name="SearchIcon" :size="16" />
					<input v-model="search" placeholder="Search" class="grow" />
					<n-text code>ESC</n-text>
					<Icon :name="CloseIcon" :size="20" class="cursor-pointer" @click="closeBox()" />
				</div>
				<n-divider />
				<n-scrollbar ref="scrollContent" class="h-96!">
					<div class="conten-wrap">
						<div v-for="group of filteredGroups" :key="group.name" class="group">
							<div class="group-title">{{ group.name }}</div>
							<n-spin :show="!!group.loading" :size="14">
								<div v-if="!group.items.length && group.loading" class="group-loading">Searching…</div>
								<div class="group-list">
									<button
										v-for="item of group.items"
										:id="item.key"
										:key="item.key"
										class="item flex items-center"
										:class="{ active: item.key === activeItem }"
										@click="callAction(item)"
										@mouseenter="activeItem = item.key"
									>
										<div class="icon min-w-7">
											<n-avatar
												v-if="item.iconImage"
												round
												:size="28"
												:src="item.iconImage"
												:img-props="{ alt: 'avatar' }"
											/>
											<Icon v-if="item.iconName" :name="item.iconName" :size="16" />
										</div>
										<div class="title grow">
											<n-highlight
												:text="item.title"
												:patterns="keywords"
												highlight-class="search-highlight"
											/>
										</div>
										<div class="label whitespace-nowrap">{{ item.label }}</div>
									</button>
								</div>
							</n-spin>
						</div>
						<div v-if="!filteredGroups.length" class="group-empty">
							We couldn't find anything matching "{{ search }}"
						</div>
					</div>
				</n-scrollbar>
				<n-divider />
				<div class="hint-bar flex items-center justify-center">
					<div class="hint flex items-center justify-center gap-1">
						<div class="icon">
							<Icon :name="ArrowEnterIcon" :size="12" />
						</div>
						<span class="label">to select</span>
					</div>
					<div class="hint flex items-center justify-center gap-1">
						<div class="icon">
							<Icon :name="ArrowSortIcon" :size="12" />
						</div>
						<span class="label">to navigate</span>
					</div>
				</div>
			</div>
		</n-card>
	</n-modal>
</template>

<script lang="ts" setup>
import type { ScrollbarInst } from "naive-ui"
import { useMagicKeys, useStorage, watchDebounced, whenever } from "@vueuse/core"
import { NAvatar, NCard, NDivider, NHighlight, NModal, NScrollbar, NSpin, NText } from "naive-ui"
import { computed, onMounted, reactive, ref, watch } from "vue"
import { useRouter } from "vue-router"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { createFuse, entityCandidates, searchFuse, toKeywords } from "@/components/common/searchDialog.helpers"
import { useFullscreenSwitch } from "@/composables/useFullscreenSwitch"
import { useNavigation } from "@/composables/useNavigation"
import { useSearchDialog } from "@/composables/useSearchDialog"
import { useThemeSwitch } from "@/composables/useThemeSwitch"
import { getNavigatorOS } from "@/utils"

/** What a recorded/rebuilt palette selection points at. `route` is a plain page jump. */
type ItemKind =
	| "route"
	| "alert"
	| "case"
	| "customer"
	| "agent"
	| "copilotRule"
	| "wazuhRule"
	| "user"
	| "story"
	| "schedulerJob"
	| "index"

interface GroupItem {
	iconName: string | null
	iconImage: string | null
	key: string
	title: string
	label: string
	tags?: string[]
	/** When set, selecting the item records it under "Recent" (serializable target). */
	recent?: { kind: ItemKind; target: string }
	action: () => void
}

interface Group {
	name: string
	items: GroupItem[]
	loading?: boolean
}

/** Fetches up to 5 entity matches for a query. Server-side sources honour the AbortSignal. */
interface RemoteProvider {
	name: string
	search: (query: string, signal: AbortSignal) => Promise<GroupItem[]>
}

const REMOTE_MIN_CHARS = 3
const REMOTE_MAX_ITEMS = 5

/** Serializable shape persisted to localStorage for the Recent group. */
interface RecentEntry {
	key: string
	title: string
	iconName: string | null
	kind: ItemKind
	target: string
}

const RECENT_LIMIT = 6

const SearchIcon = "ion:search-outline"
const ArrowEnterIcon = "fluent:arrow-enter-left-24-regular"
const ArrowSortIcon = "fluent:arrow-sort-24-regular"
const FullScreenIcon = "fluent:full-screen-maximize-24-regular"
const DarkModeIcon = "ion:moon-outline"
const CloseIcon = "carbon:close"
const RecentIcon = "carbon:recently-viewed"
const AlertEntityIcon = "carbon:warning-hex"
const CaseEntityIcon = "carbon:folder"
const CustomerEntityIcon = "carbon:user"
const AgentEntityIcon = "carbon:network-3"
const CopilotRuleEntityIcon = "carbon:search-locate"
const WazuhRuleEntityIcon = "carbon:rule"
const UserEntityIcon = "carbon:user-avatar"
const StoryEntityIcon = "carbon:book"
const SchedulerJobEntityIcon = "carbon:calendar"
const IndexEntityIcon = "carbon:data-base"
const AddCustomerIcon = "carbon:user-follow"
const ConnectorsIcon = "carbon:hybrid-networking"
const NewCaseIcon = "carbon:folder-add"
const NewTemplateIcon = "carbon:document-add"
const NewExclusionIcon = "carbon:rule"
const NewUserIcon = "carbon:user-admin"

/** Curated page/tab jumps. Every routeName is verified to exist in the router. */
const NAV_LINKS: { title: string; routeName: string; icon: string; tags: string[] }[] = [
	{ title: "Overview", routeName: "Overview", icon: "carbon:dashboard", tags: ["home", "dashboard"] },
	{
		title: "AI Analyst",
		routeName: "AiAnalyst",
		icon: "carbon:machine-learning-model",
		tags: ["ai", "talon", "analyst"]
	},
	{
		title: "Detections Catalog",
		routeName: "DetectionCatalog",
		icon: "carbon:catalog",
		tags: ["detection", "rules", "wazuh", "coverage", "compliance"]
	},
	{ title: "Customers", routeName: "Customers", icon: "carbon:user-multiple", tags: ["tenant", "client"] },
	{ title: "SIEM Alerts", routeName: "Alerts-SIEM", icon: "carbon:warning-alt", tags: ["siem", "alerts", "wazuh"] },
	{ title: "Event Search", routeName: "EventSearch", icon: "carbon:search", tags: ["events", "logs"] },
	{ title: "Dashboards", routeName: "Dashboards", icon: "carbon:dashboard-reference", tags: ["grafana"] },
	{
		title: "MITRE ATT&CK",
		routeName: "Alerts-Mitre",
		icon: "carbon:security",
		tags: ["mitre", "attack", "tactics", "techniques"]
	},
	{
		title: "Atomic Red Team",
		routeName: "Alerts-AtomicRedTeam",
		icon: "carbon:chemistry",
		tags: ["atomic", "red team", "tests"]
	},
	{
		title: "Incident Alerts",
		routeName: "IncidentManagement-Alerts",
		icon: "carbon:warning-hex",
		tags: ["incident", "alerts"]
	},
	{
		title: "Incident Cases",
		routeName: "IncidentManagement-Cases",
		icon: "carbon:folder",
		tags: ["incident", "cases"]
	},
	{
		title: "Case Templates",
		routeName: "IncidentManagement-CaseTemplates",
		icon: "carbon:document-multiple-01",
		tags: ["case", "templates"]
	},
	{
		title: "Incident Sources",
		routeName: "IncidentManagement-Sources",
		icon: "carbon:data-share",
		tags: ["sources", "ingest"]
	},
	{ title: "Agents", routeName: "Agents", icon: "carbon:network-3", tags: ["endpoints", "wazuh"] },
	{
		title: "Index Management",
		routeName: "Indices",
		icon: "carbon:data-base",
		tags: ["indices", "index", "opensearch"]
	},
	{ title: "Healthcheck", routeName: "Healthcheck", icon: "carbon:activity", tags: ["health", "status"] },
	{ title: "Metrics", routeName: "Metrics", icon: "carbon:chart-line", tags: ["influxdb", "metrics"] },
	{ title: "Scheduler", routeName: "Scheduler", icon: "carbon:calendar", tags: ["jobs", "cron"] },
	{ title: "Users", routeName: "Users", icon: "carbon:group", tags: ["rbac", "accounts"] },
	{ title: "CoPilot Actions", routeName: "CopilotActions", icon: "carbon:play", tags: ["copilot", "response"] },
	{
		title: "CoPilot Searches",
		routeName: "CopilotSearches",
		icon: "carbon:search-locate",
		tags: ["copilot", "rules"]
	},
	{
		title: "Vulnerability Overview",
		routeName: "VulnerabilityOverview",
		icon: "carbon:debug",
		tags: ["vulnerability", "cve", "vulnerabilities"]
	},
	{ title: "SCA Overview", routeName: "ScaOverview", icon: "carbon:certificate-check", tags: ["sca", "benchmark"] },
	{ title: "GitHub Audit", routeName: "GitHubAudit", icon: "carbon:logo-github", tags: ["github", "audit"] }
]

const showSearchBox = ref(false)
const search = ref("")
const activeItem = ref<string | null>(null)
const commandIcon = ref("⌘")
const scrollContent = ref<(ScrollbarInst & { $el: HTMLElement }) | null>(null)
const router = useRouter()
const {
	routeCustomer,
	routeAgent,
	routeIncidentManagementAlerts,
	routeIncidentManagementCases,
	routeIncidentManagementCaseNew,
	routeIncidentManagementCaseTemplateNew,
	routeIncidentManagementExclusionRuleNew,
	routeUserNew,
	routeCopilotSearchRule,
	routeDetectionCatalogWazuhRule,
	routeUser,
	routeDetectionCatalogStory,
	routeSchedulerJob,
	routeIndex
} = useNavigation()

const recentStore = useStorage<RecentEntry[]>("copilot-search-recent", [])

function goToRoute(name: string) {
	router.push({ name })
}

/** kind → navigator. Sibling to ENTITY_ICONS; keeps the kind mapping in one table. */
const ENTITY_NAV: Record<ItemKind, (target: string) => void> = {
	route: goToRoute,
	alert: target => routeIncidentManagementAlerts(Number(target)).navigate(),
	case: target => routeIncidentManagementCases(Number(target)).navigate(),
	customer: target => routeCustomer({ code: target }).navigate(),
	agent: target => routeAgent(target).navigate(),
	copilotRule: target => routeCopilotSearchRule(target).navigate(),
	wazuhRule: target => routeDetectionCatalogWazuhRule(Number(target)).navigate(),
	user: target => routeUser(Number(target)).navigate(),
	story: target => routeDetectionCatalogStory(target).navigate(),
	schedulerJob: target => routeSchedulerJob(target).navigate(),
	index: target => routeIndex(target).navigate()
}

/** Rebuilds and runs a persisted target (used by Recent items). */
function runTarget(kind: ItemKind, target: string) {
	ENTITY_NAV[kind](target)
}

// Static groups — built once (route helpers are stable), fuzzy-filtered via a memoized Fuse index.
const navigateGroup: Group = {
	name: "Navigate",
	items: NAV_LINKS.map(link => ({
		iconName: link.icon,
		iconImage: null,
		key: `nav:${link.routeName}`,
		title: link.title,
		label: "Page",
		tags: link.tags,
		recent: { kind: "route", target: link.routeName },
		action: () => goToRoute(link.routeName)
	}))
}

const actionsGroup: Group = {
	name: "Actions",
	items: [
		{
			iconName: AddCustomerIcon,
			iconImage: null,
			key: "action:add-customer",
			title: "Add a Customer",
			label: "Action",
			tags: ["new", "customer", "tenant"],
			action() {
				routeCustomer({ action: "add-customer" }).navigate()
				useSearchDialog().openAddCustomer()
			}
		},
		{
			iconName: ConnectorsIcon,
			iconImage: null,
			key: "action:connectors",
			title: "Open Connectors",
			label: "Action",
			tags: ["connector", "integration", "configure"],
			action: () => goToRoute("Connectors")
		},
		{
			iconName: NewCaseIcon,
			iconImage: null,
			key: "action:new-case",
			title: "New Case",
			label: "Action",
			tags: ["incident", "case", "create"],
			action: () => routeIncidentManagementCaseNew().navigate()
		},
		{
			iconName: NewTemplateIcon,
			iconImage: null,
			key: "action:new-case-template",
			title: "New Case Template",
			label: "Action",
			tags: ["case", "template", "create"],
			action: () => routeIncidentManagementCaseTemplateNew().navigate()
		},
		{
			iconName: NewExclusionIcon,
			iconImage: null,
			key: "action:new-exclusion",
			title: "New Exclusion Rule",
			label: "Action",
			tags: ["exclusion", "rule", "tuning", "create"],
			action: () => routeIncidentManagementExclusionRuleNew().navigate()
		},
		{
			iconName: NewUserIcon,
			iconImage: null,
			key: "action:new-user",
			title: "New User",
			label: "Action",
			tags: ["user", "account", "create"],
			action: () => routeUserNew().navigate()
		},
		{
			iconName: FullScreenIcon,
			iconImage: null,
			key: "action:fullscreen",
			title: "Toggle fullscreen",
			label: "Action",
			tags: ["fullscreen", "display"],
			action: () => useFullscreenSwitch().toggle()
		},
		{
			iconName: DarkModeIcon,
			iconImage: null,
			key: "action:dark-mode",
			title: "Toggle dark mode",
			label: "Action",
			tags: ["theme", "dark", "light"],
			action: () => useThemeSwitch().toggle()
		}
	]
}

const STATIC_GROUPS = [navigateGroup, actionsGroup]
const staticFuses = STATIC_GROUPS.map(group => createFuse(group.items, ["title", "tags"]))

/** Fuzzy-filtered nav/action groups. Depends only on `search`, so remote results don't rebuild the Fuse indexes. */
const filteredStaticGroups = computed<Group[]>(() =>
	STATIC_GROUPS.map((group, i) => ({ name: group.name, items: searchFuse(staticFuses[i], search.value, group.items) })).filter(
		group => group.items.length
	)
)

const ENTITY_ICONS: Record<ItemKind, string> = {
	route: RecentIcon,
	alert: AlertEntityIcon,
	case: CaseEntityIcon,
	customer: CustomerEntityIcon,
	agent: AgentEntityIcon,
	copilotRule: CopilotRuleEntityIcon,
	wazuhRule: WazuhRuleEntityIcon,
	user: UserEntityIcon,
	story: StoryEntityIcon,
	schedulerJob: SchedulerJobEntityIcon,
	index: IndexEntityIcon
}

/** Builds a selectable, recent-tracked entity item that navigates to a detail page. */
function entityItem(kind: ItemKind, target: string, title: string, label: string): GroupItem {
	return {
		iconName: ENTITY_ICONS[kind],
		iconImage: null,
		key: `entity:${kind}:${target}`,
		title: title || target,
		label,
		tags: [kind, target],
		recent: { kind, target },
		action: () => runTarget(kind, target)
	}
}

/** Maps API rows to entity items; `pick` returns `[target, title, label]` for one row. */
function toEntityItems<T>(kind: ItemKind, rows: T[], pick: (row: T) => [string, string, string]): GroupItem[] {
	return rows.map(row => entityItem(kind, ...pick(row)))
}

/** Dynamic "jump to entity by ID" quick items, derived from a numeric query. */
const entityItems = computed<GroupItem[]>(() =>
	entityCandidates(search.value).map(({ kind, target, title }) => entityItem(kind, target, title, "Jump"))
)

// --- Remote entity search --------------------------------------------------
// Every provider searches through an API — the palette never downloads a full
// entity list to filter it client-side.

const SEARCH_LIMIT = { limit: REMOTE_MAX_ITEMS }

const REMOTE_PROVIDERS: RemoteProvider[] = [
	{
		name: "Customers",
		async search(query, signal) {
			const res = await Api.customers.searchCustomers(query, REMOTE_MAX_ITEMS, signal)
			return toEntityItems("customer", res.data.customers ?? [], c => [c.customer_code, c.customer_name, c.customer_code])
		}
	},
	{
		name: "Alerts",
		async search(query, signal) {
			const res = await Api.incidentManagement.alerts.getAlertsList(
				{ filter: { title: query }, page: 1, pageSize: REMOTE_MAX_ITEMS },
				signal
			)
			return toEntityItems("alert", res.data.alerts, a => [String(a.id), a.alert_name, `#${a.id}`])
		}
	},
	{
		name: "Cases",
		async search(query, signal) {
			const res = await Api.incidentManagement.cases.searchCasesByName(query, { page: 1, pageSize: REMOTE_MAX_ITEMS }, signal)
			return toEntityItems("case", res.data.cases, c => [String(c.id), c.case_name, `#${c.id}`])
		}
	},
	{
		name: "Agents",
		async search(query, signal) {
			const res = await Api.agents.getAgents({ search: query, ...SEARCH_LIMIT }, signal)
			return toEntityItems("agent", res.data.agents, a => [
				a.agent_id,
				a.hostname || a.label || a.agent_id,
				a.customer_code ?? a.ip_address
			])
		}
	},
	{
		name: "Users",
		async search(query, signal) {
			const res = await Api.users.getUsers({ search: query, ...SEARCH_LIMIT }, signal)
			return toEntityItems("user", res.data.users, u => [String(u.id), u.username, u.email])
		}
	},
	{
		name: "Detection Rules",
		async search(query, signal) {
			const res = await Api.copilotSearches.getRules({ search: query, ...SEARCH_LIMIT }, signal)
			return toEntityItems("copilotRule", res.data.rules, r => [r.id, r.name, r.severity])
		}
	},
	{
		name: "Wazuh Rules",
		async search(query, signal) {
			const res = await Api.detectionCatalog.listWazuhRules(undefined, { search: query, ...SEARCH_LIMIT }, signal)
			return toEntityItems("wazuhRule", res.data.rules.filter(r => r.id != null), r => [String(r.id), r.description, `#${r.id}`])
		}
	},
	{
		name: "Detection Stories",
		async search(query, signal) {
			const res = await Api.detectionCatalog.listStories({ search: query, ...SEARCH_LIMIT }, signal)
			return toEntityItems("story", res.data.stories, s => [s.name, s.name, `${s.detection_count} detections`])
		}
	},
	{
		name: "Scheduler Jobs",
		async search(query, signal) {
			const res = await Api.scheduler.getAllJobs({ search: query, ...SEARCH_LIMIT }, signal)
			return toEntityItems("schedulerJob", res.data.jobs, j => [j.id, j.name, j.id])
		}
	},
	{
		name: "Indices",
		async search(query, signal) {
			const res = await Api.indices.getIndices({ search: query, ...SEARCH_LIMIT }, signal)
			return toEntityItems("index", res.data.indices_stats, i => [i.index, i.index, `${i.docs_count} docs`])
		}
	}
]

const remoteGroups = reactive(
	REMOTE_PROVIDERS.map(provider => ({ name: provider.name, items: [] as GroupItem[], loading: false }))
)
let remoteAbort: AbortController | null = null

function clearRemoteGroups() {
	remoteAbort?.abort()
	remoteAbort = null
	remoteGroups.forEach(group => {
		group.items = []
		group.loading = false
	})
}

function runRemoteSearch(query: string) {
	remoteAbort?.abort()

	if (query.trim().length < REMOTE_MIN_CHARS) {
		clearRemoteGroups()
		return
	}

	const controller = new AbortController()
	remoteAbort = controller

	REMOTE_PROVIDERS.forEach((provider, index) => {
		remoteGroups[index].loading = true
		provider
			.search(query, controller.signal)
			.then(items => {
				if (!controller.signal.aborted) remoteGroups[index].items = items
			})
			.catch(() => {
				if (!controller.signal.aborted) remoteGroups[index].items = []
			})
			.finally(() => {
				if (!controller.signal.aborted) remoteGroups[index].loading = false
			})
	})
}

watchDebounced(search, () => runRemoteSearch(search.value), { debounce: 250, maxWait: 1500 })

const recentItems = computed<GroupItem[]>(() =>
	recentStore.value.map(entry => ({
		iconName: entry.iconName ?? RecentIcon,
		iconImage: null,
		key: `recent:${entry.key}`,
		title: entry.title,
		label: "Recent",
		action: () => runTarget(entry.kind, entry.target)
	}))
)

const keywords = computed<string[]>(() => toKeywords(search.value))

const filteredGroups = computed<Group[]>(() => {
	const kws = keywords.value

	if (!kws.length) {
		const groups: Group[] = []
		if (recentItems.value.length) groups.push({ name: "Recent", items: recentItems.value })
		groups.push(...STATIC_GROUPS)
		return groups
	}

	const groups: Group[] = []
	if (entityItems.value.length) groups.push({ name: "Quick jump", items: entityItems.value })

	// Remote entity results — shown while loading (spinner) or once they have hits.
	for (const group of remoteGroups) {
		if (group.loading || group.items.length) {
			groups.push({ name: group.name, items: group.items, loading: group.loading })
		}
	}

	groups.push(...filteredStaticGroups.value)

	return groups
})

const filteredFlattenItems = computed<GroupItem[]>(() => filteredGroups.value.flatMap(group => group.items))

// Keep a valid highlight and pre-select the first result while typing, so Enter fires immediately.
watch(filteredFlattenItems, items => {
	if (!items.length) {
		activeItem.value = null
		return
	}
	if (!items.some(item => item.key === activeItem.value)) {
		activeItem.value = search.value.trim() ? items[0].key : null
	}
})

function recordRecent(item: GroupItem) {
	if (!item.recent) return

	const entry: RecentEntry = {
		key: `${item.recent.kind}:${item.recent.target}`,
		title: item.title,
		iconName: item.iconName,
		kind: item.recent.kind,
		target: item.recent.target
	}
	recentStore.value = [entry, ...recentStore.value.filter(e => e.key !== entry.key)].slice(0, RECENT_LIMIT)
}

function openBox(e?: MouseEvent) {
	if (!showSearchBox.value) {
		showSearchBox.value = true

		setTimeout(() => {
			search.value = ""
			activeItem.value = null
		}, 100)
	}
	return e
}

function closeBox() {
	showSearchBox.value = false
	search.value = ""
	activeItem.value = null
	clearRemoteGroups()
}

function callAction(item: GroupItem) {
	item.action()
	recordRecent(item)
	closeBox()
}

function navigateItem(direction: "next" | "prev") {
	const items = filteredFlattenItems.value
	if (!items.length) return

	const currentIndex = items.findIndex(item => item.key === activeItem.value)
	const isAtEnd = currentIndex === items.length - 1
	const isAtStart = currentIndex === 0
	const nextItem = items[currentIndex + 1]
	const prevItem = items[currentIndex - 1]
	const firstItem = items[0]
	const lastItem = items.at(-1)

	if (direction === "next") {
		activeItem.value = (activeItem.value === null || isAtEnd) && firstItem ? firstItem.key : (nextItem?.key ?? null)
	} else {
		activeItem.value = (activeItem.value === null || isAtStart) && lastItem ? lastItem.key : (prevItem?.key ?? null)
	}
	centerItem()
}

function nextItem() {
	navigateItem("next")
}

function prevItem() {
	navigateItem("prev")
}

function performAction() {
	const items = filteredFlattenItems.value
	// Fall back to the first result so Enter works without arrowing down first.
	const item = items.find(item => item.key === activeItem.value) ?? items[0]
	if (item) {
		callAction(item)
	}
}

function centerItem() {
	const element = document.getElementById(activeItem.value ?? "")
	if (element && scrollContent.value) {
		element.scrollIntoView({ block: "nearest" })
	}
}

onMounted(() => {
	const isWindows = getNavigatorOS() === "Windows"
	commandIcon.value = isWindows ? "CTRL" : "⌘"

	const keys = useMagicKeys()
	const ActiveCMD = isWindows ? keys["ctrl+k"] : keys["cmd+k"]
	const Enter = keys.enter

	useSearchDialog().trigger(openBox)

	if (ActiveCMD) {
		whenever(ActiveCMD, () => {
			openBox()
		})
	}

	if (Enter) {
		whenever(Enter, () => {
			if (showSearchBox.value) {
				performAction()
			}
		})
	}
})
</script>

<style lang="scss" scoped>
.search-box-modal {
	.search-box {
		border-radius: 4px;

		.search-input {
			height: 50px;
			gap: 20px;
			padding: 20px;

			input {
				background: transparent;
				outline: none;
				border: none;
				min-width: 100px;
			}

			.n-text--code {
				white-space: nowrap;
			}
		}

		.n-divider {
			margin-top: 0;
			margin-bottom: 0;
		}

		.conten-wrap {
			padding-bottom: 30px;

			.group-empty {
				text-align: center;
				padding: 30px 0 40px 0;
			}
			.group-loading {
				padding: 6px 20px;
				opacity: 0.6;
				font-size: 0.9em;
			}
			.group {
				padding: 0 10px;
				.group-title {
					opacity: 0.6;
					margin-bottom: 5px;
					padding: 5px 10px;
					padding-top: 20px;
				}
				.group-list {
					.item {
						padding: 7px 10px;
						gap: 10px;
						cursor: pointer;
						border-radius: 10px;
						width: 100%;
						text-align: left;

						.icon {
							width: 28px;
							height: 28px;
							border-radius: 50%;
							background-color: rgba(var(--primary-color-rgb) / 0.15);
							display: flex;
							justify-content: center;
							align-items: center;
						}
						.title {
							font-weight: bold;

							:deep(.search-highlight) {
								background-color: rgba(var(--primary-color-rgb) / 0.2);
								color: var(--primary-color);
								border-radius: 3px;
								padding: 0 1px;
							}
						}
						.label {
							opacity: 0.8;
							font-size: 0.9em;
						}

						&.active {
							background-color: var(--hover-color);
						}
						&:hover {
							box-shadow: 0px 0px 0px 1px var(--primary-color) inset;
						}
					}
				}
			}
		}

		.hint-bar {
			font-size: 12px;
			gap: 20px;
			padding: 10px 0;

			.icon {
				background-color: rgba(255, 255, 255, 0.3);
				width: 18px;
				height: 18px;
				padding-top: 1px;
				text-align: center;
				border-radius: 4px;
				display: flex;
				align-items: center;
				justify-content: center;
			}
			.label {
				opacity: 0.7;
			}
		}
	}
}
</style>
