<template>
	<n-modal v-model:show="showSearchBox" class="search-box-modal">
		<n-card content-class="p-0!" class="w-150!" :bordered="false" size="huge" role="dialog" aria-modal="true">
			<div class="search-box" @keydown.up="prevItem()" @keydown.down="nextItem()">
				<div class="search-input flex items-center">
					<Icon :name="DIALOG_ICONS.search" :size="16" />
					<input v-model="search" placeholder="Search" class="grow" />
					<n-text code>ESC</n-text>
					<Icon :name="DIALOG_ICONS.close" :size="20" class="cursor-pointer" @click="closeBox()" />
				</div>
				<n-divider />
				<n-scrollbar ref="scrollContent" class="h-96!">
					<div class="conten-wrap">
						<div v-for="group of filteredGroups" :key="group.name" class="group">
							<div class="group-title">{{ group.name }}</div>
							<n-spin :show="group.loading">
								<div class="group-list">
									<button
										v-for="item of group.items"
										:id="item.key.toString()"
										:key="item.key"
										class="item flex items-center"
										:class="{ active: item.key === activeItem }"
										@click="callAction(item.action)"
									>
										<div class="icon shrink-0">
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
											<Highlighter
												highlight-class-name="highlight"
												:search-words="keywords"
												auto-escape
												:text-to-highlight="item.title"
											/>
										</div>
										<div class="label text-right">{{ item.label }}</div>
									</button>
								</div>
							</n-spin>
						</div>
						<div v-if="!filteredGroups.length" class="group-empty">No results found for "{{ search }}"</div>
					</div>
				</n-scrollbar>
				<n-divider />
				<div class="hint-bar flex items-center justify-center">
					<div class="hint flex items-center justify-center gap-1">
						<div class="icon">
							<Icon :name="DIALOG_ICONS.arrowEnter" :size="12" />
						</div>
						<span class="label">to select</span>
					</div>
					<div class="hint flex items-center justify-center gap-1">
						<div class="icon">
							<Icon :name="DIALOG_ICONS.arrowSort" :size="12" />
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
import type { RouteRecordRaw } from "vue-router"
import { useMagicKeys, watchDebounced, whenever } from "@vueuse/core"
import toNumber from "lodash/toNumber"
import { NAvatar, NCard, NDivider, NModal, NScrollbar, NSpin, NText } from "naive-ui"
import { computed, onMounted, ref } from "vue"
import Highlighter from "vue-highlight-words"
import { useRouter } from "vue-router"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useFullscreenSwitch } from "@/composables/common/useFullscreenSwitch"
import { useNavigation } from "@/composables/common/useNavigation"
import { useSearchDialog } from "@/composables/common/useSearchDialog"
import { useThemeSwitch } from "@/composables/common/useThemeSwitch"
import { ICONS } from "@/const"
import { getNavigatorOS } from "@/utils"

const MULTIPLE_SLASHES_REGEX = /\/+/g
const TRAILING_SLASH_REGEX = /\/$/

interface GroupItem {
	iconName: string | null
	iconImage: string | null
	key: number | string
	title: string
	label: string
	tags?: string[]
	action: () => void
}

interface Group {
	name: string
	items: GroupItem[]
	loading: boolean
}

type Groups = Group[]

interface RouteFilter {
	type: "exclude" | "include"
	names: string[]
}

const DIALOG_ICONS = {
	search: "ion:search-outline",
	close: "ion:close",
	arrowEnter: "fluent:arrow-enter-left-24-regular",
	arrowSort: "fluent:arrow-sort-24-regular",
	fullscreen: "fluent:full-screen-maximize-24-regular",
	theme: "ion:moon-outline",
	document: "carbon:network-3"
} as const

const INCLUDED_ROUTES = [
	"Dashboard",
	"AgentsList",
	"CustomersList",
	"PackagesList",
	"PortsList",
	"ProcessesList",
	"VulnerabilitiesList",
	"AlertsList",
	"Profile"
] as const

const router = useRouter()
const { routeAgent, routePackage, routeProcess, routeCustomer, routePort } = useNavigation()
const showSearchBox = ref(false)
const search = ref("")
const activeItem = ref<null | string | number>(null)
const scrollContent = ref<(ScrollbarInst & { $el: HTMLElement }) | null>(null)

function createItem(
	key: number | string,
	title: string,
	label: string,
	action: () => void,
	iconName: string | null = null,
	iconImage: string | null = null
): GroupItem {
	return {
		iconName,
		iconImage,
		key,
		title,
		label,
		action
	}
}

const AgentsGroup = ref<Group>({
	name: "Agents",
	items: [],
	loading: false
})

const CustomersGroup = ref<Group>({
	name: "Customers",
	items: [],
	loading: false
})

const ProcessesGroup = ref<Group>({
	name: "Critical Processes",
	items: [],
	loading: false
})

const PackagesGroup = ref<Group>({
	name: "Packages",
	items: [],
	loading: false
})

const PortsGroup = ref<Group>({
	name: "Ports",
	items: [],
	loading: false
})

const ActionsGroup = ref<Group>({
	name: "Actions",
	items: [
		createItem(1, "Toggle fullscreen", "Action", () => useFullscreenSwitch().toggle(), DIALOG_ICONS.fullscreen),
		createItem(2, "Toggle theme", "Action", () => useThemeSwitch().toggle(), DIALOG_ICONS.theme)
	],
	loading: false
})

function buildFullPath(route: RouteRecordRaw, parentPath: string): string {
	if (route.path.startsWith("/")) return route.path
	if (route.path === "") return parentPath
	return parentPath ? `${parentPath}/${route.path}` : `/${route.path}`
}

function normalizePath(path: string): string {
	return path.replace(MULTIPLE_SLASHES_REGEX, "/").replace(TRAILING_SLASH_REGEX, "") || "/"
}

function shouldIncludeRoute(routeName: string, filter?: RouteFilter): boolean {
	if (!filter) return true
	return filter.type === "exclude" ? !filter.names.includes(routeName) : filter.names.includes(routeName)
}

function getAllRoutes(
	routeList: RouteRecordRaw[],
	parentPath = "",
	filter?: RouteFilter
): Array<RouteRecordRaw & { fullPath: string }> {
	const routes: Array<RouteRecordRaw & { fullPath: string }> = []

	for (const route of routeList) {
		const fullPath = normalizePath(buildFullPath(route, parentPath))

		if (route.name && route.meta?.title && shouldIncludeRoute(route.name as string, filter)) {
			routes.push({ ...route, fullPath })
		}

		if (route.children) {
			routes.push(...getAllRoutes(route.children, fullPath, filter))
		}
	}

	return routes
}

const PagesGroup = computed<Group>(() => {
	const allRoutes = getAllRoutes(router.getRoutes(), "", {
		type: "include",
		names: [...INCLUDED_ROUTES]
	})

	const items: GroupItem[] = allRoutes.map((route, index) => {
		const routeName = route.name as string
		const title = route.meta?.title || routeName || route.path

		return {
			iconName: DIALOG_ICONS.document,
			iconImage: null,
			key: `page-${routeName}-${index}`,
			title,
			label: route.fullPath,
			action: () => router.push({ name: route.name })
		}
	})

	return {
		name: "Pages",
		items,
		loading: false
	}
})

const groups = computed<Groups>(() => [
	AgentsGroup.value,
	CustomersGroup.value,
	PackagesGroup.value,
	PortsGroup.value,
	ProcessesGroup.value,
	PagesGroup.value,
	ActionsGroup.value
])

const keywords = computed<string[]>(() => (search.value.length > 1 ? search.value.split(" ").filter(Boolean) : []))

function matchesKeyword(text: string, keywords: string[]): boolean {
	return keywords.some(k => text.toLowerCase().includes(k.toLowerCase()))
}

const filteredGroups = computed<Groups>(() => {
	if (!keywords.value.length) {
		return groups.value.filter(group => group.items.length || group.loading)
	}

	return groups.value
		.map(group => ({
			name: group.name,
			items: group.items.filter(
				item =>
					matchesKeyword(item.title, keywords.value) ||
					item.tags?.some(tag => matchesKeyword(tag, keywords.value))
			),
			loading: group.loading
		}))
		.filter(group => group.items.length || group.loading)
})

const filteredFlattenItems = computed<GroupItem[]>(() => filteredGroups.value.flatMap(group => group.items))

function resetSearch() {
	search.value = ""
	activeItem.value = null
}

function loadAsyncData() {
	getAgentsList()
	getCustomersList()
	getPackagesList()
	getProcessesList()
	getPortsList()
}

function openBox(e?: MouseEvent) {
	if (!showSearchBox.value) {
		showSearchBox.value = true
		loadAsyncData()
		setTimeout(resetSearch, 100)
	}
	return e
}

function closeBox() {
	showSearchBox.value = false
	resetSearch()
}

function callAction(action: () => void) {
	action()
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
	const item = filteredFlattenItems.value.find(item => item.key === activeItem.value)
	item && callAction(item.action)
}

function centerItem() {
	const element = document.getElementById(String(activeItem.value || ""))
	element && scrollContent.value && element.scrollIntoView({ block: "nearest" })
}

let abortControllerAgents: AbortController | null = null
let abortControllerCustomers: AbortController | null = null
let abortControllerPackages: AbortController | null = null
let abortControllerProcesses: AbortController | null = null
let abortControllerPorts: AbortController | null = null

function getAgentsList() {
	abortControllerAgents?.abort()
	abortControllerAgents = new AbortController()

	AgentsGroup.value.loading = true

	Api.agents
		.list(
			{
				page_size: search.value ? 10 : 5,
				page: 1,
				hostname: search.value || undefined
			},
			abortControllerAgents.signal
		)
		.then(res => {
			AgentsGroup.value.items = res.data.agents.map(agent =>
				createItem(
					agent.id,
					agent.hostname,
					agent.ip_address || "",
					() => routeAgent(agent.id).navigate(),
					ICONS.agent
				)
			)
		})
		.catch(() => {
			AgentsGroup.value.items = []
		})
		.finally(() => {
			AgentsGroup.value.loading = false
		})
}

function getCustomersList() {
	abortControllerCustomers?.abort()
	abortControllerCustomers = new AbortController()

	CustomersGroup.value.loading = true

	Api.customers
		.list(
			{
				page_size: search.value ? 10 : 5,
				page: 1,
				name: search.value || undefined
			},
			abortControllerCustomers.signal
		)
		.then(res => {
			CustomersGroup.value.items = res.data.results.map(customer =>
				createItem(
					customer.id,
					customer.name,
					customer.code || "",
					() => routeCustomer(customer.id).navigate(),
					ICONS.customers
				)
			)
		})
		.catch(() => {
			CustomersGroup.value.items = []
		})
		.finally(() => {
			CustomersGroup.value.loading = false
		})
}

function getProcessesList() {
	abortControllerProcesses?.abort()
	abortControllerProcesses = new AbortController()

	ProcessesGroup.value.loading = true

	Api.processes
		.searchRaw(
			{
				page_size: search.value ? 10 : 5,
				page: 1,
				name: search.value || undefined,
				is_critical: true
			},
			abortControllerProcesses.signal
		)
		.then(res => {
			ProcessesGroup.value.items = res.data.results.map(process =>
				createItem(
					process.id,
					process.name,
					process.category || "",
					() => routeProcess(process.id).navigate(),
					ICONS.processes
				)
			)
		})
		.catch(() => {
			ProcessesGroup.value.items = []
		})
		.finally(() => {
			ProcessesGroup.value.loading = false
		})
}

function getPackagesList() {
	abortControllerPackages?.abort()
	abortControllerPackages = new AbortController()

	if (!search.value) {
		PackagesGroup.value.loading = false
		PackagesGroup.value.items = []
		return
	}

	PackagesGroup.value.loading = true

	Api.packages
		.searchRaw(
			{
				name: search.value || undefined,
				page_size: search.value ? 10 : 5,
				page: 1
			},
			abortControllerPackages.signal
		)
		.then(res => {
			PackagesGroup.value.items = res.data.results.map(pkg =>
				createItem(
					`package-${pkg.id}`,
					pkg.name,
					pkg.version || "",
					() => routePackage(pkg.id).navigate(),
					ICONS.packages
				)
			)
		})
		.catch(() => {
			PackagesGroup.value.items = []
		})
		.finally(() => {
			PackagesGroup.value.loading = false
		})
}

function getPortsList() {
	abortControllerPorts?.abort()
	abortControllerPorts = new AbortController()

	if (!search.value) {
		PortsGroup.value.loading = false
		PortsGroup.value.items = []
		return
	}

	PortsGroup.value.loading = true

	Api.ports
		.searchRaw(
			{
				local_port: search.value ? toNumber(search.value) : undefined,
				page_size: 5,
				page: 1
			},
			abortControllerPorts.signal
		)
		.then(res => {
			PortsGroup.value.items = res.data.results.map(port =>
				createItem(
					`port-${port.id}`,
					port.local_port.toString(),
					port.protocol || "",
					() => routePort(port.id).navigate(),
					ICONS.ports
				)
			)
		})
		.catch(() => {
			PortsGroup.value.items = []
		})
		.finally(() => {
			PortsGroup.value.loading = false
		})
}

watchDebounced(
	search,
	() => {
		loadAsyncData()
	},
	{ debounce: 300, maxWait: 5000 }
)

onMounted(() => {
	const isWindows = getNavigatorOS() === "Windows"

	const keys = useMagicKeys()
	const activeCMD = isWindows ? keys["ctrl+\\"] : keys["cmd+\\"]
	const enterCHR = keys.enter

	useSearchDialog().setup(openBox)

	if (activeCMD) {
		whenever(activeCMD, () => {
			openBox()
		})
	}

	if (enterCHR) {
		whenever(enterCHR, () => {
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
