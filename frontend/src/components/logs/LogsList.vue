<template>
	<div class="logs-list">
		<div ref="header" class="header flex items-center justify-end gap-2">
			<div class="info flex grow gap-2">
				<n-popover overlap placement="bottom-start">
					<template #trigger>
						<div class="bg-default rounded-lg">
							<n-button size="small" class="cursor-help!">
								<template #icon>
									<Icon :name="InfoIcon" />
								</template>
							</n-button>
						</div>
					</template>
					<div class="flex flex-col gap-2">
						<div class="box">
							Total :
							<code>{{ total }}</code>
						</div>
						<div class="box">
							Event Info :
							<code>{{ eventInfoTotal }}</code>
						</div>
						<div class="box text-error">
							Event Error :
							<code>{{ eventErrorTotal }}</code>
						</div>
					</div>
				</n-popover>

				<n-button size="small" type="error" ghost :loading="loadingPurge" @click="showPurgeConfirm = true">
					<div class="flex items-center gap-2">
						<Icon :name="TrashIcon" :size="16" />
						<span class="xs:block hidden">Purge</span>
					</div>
				</n-button>
			</div>
			<n-pagination
				v-model:page="currentPage"
				v-model:page-size="pageSize"
				:page-slot="pageSlot"
				:show-size-picker="showSizePicker"
				:page-sizes="pageSizes"
				:item-count="total"
				:simple="simpleMode"
			/>
			<n-popover :show="showFilters" trigger="manual" overlap placement="right" class="px-0!">
				<template #trigger>
					<div class="bg-default rounded-lg">
						<n-badge :show="filtered" dot type="success" :offset="[-4, 0]">
							<n-button size="small" @click="showFilters = true">
								<template #icon>
									<Icon :name="FilterIcon" />
								</template>
							</n-button>
						</n-badge>
					</div>
				</template>
				<LogsFilters
					v-model:type="filterType"
					v-model:value="filterValue"
					v-model:filtered="filtered"
					:users="usersList"
					:loading-users="loadingUsers"
					@submit="getData()"
					@close="showFilters = false"
				/>
			</n-popover>
		</div>
		<n-spin :show="loading">
			<div class="my-3 flex min-h-52 flex-col gap-2">
				<template v-if="logsList.length">
					<LogItem
						v-for="log of itemsPaginated"
						:key="log.id"
						:log="log"
						:users="usersList"
						class="item-appear item-appear-bottom item-appear-005"
					/>
				</template>
				<template v-else>
					<n-empty v-if="!loading" description="No Logs found" class="h-48 justify-center" />
				</template>
			</div>
		</n-spin>
		<div class="footer flex justify-end">
			<n-pagination
				v-if="itemsPaginated.length > 3"
				v-model:page="currentPage"
				:page-size="pageSize"
				:item-count="total"
				:page-slot="6"
			/>
		</div>

		<n-modal v-model:show="showPurgeConfirm" preset="dialog" type="warning" title="Purge Logs">
			<div class="mt-5 flex flex-col gap-2">
				<div>Are you sure you want to purge Logs ?</div>
				<n-select
					v-model:value="purgeSelected"
					:options="purgeOptions"
					:disabled="loadingPurge"
					placeholder="Select time range"
				/>
			</div>
			<template #action>
				<div class="flex gap-3">
					<n-button size="small" ghost @click="showPurgeConfirm = false">Cancel</n-button>
					<n-button size="small" type="warning" :loading="loadingPurge" @click="purge()">
						Yes I'm sure
					</n-button>
				</div>
			</template>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { Log, LogsQuery, LogsQueryTimeRange, LogsQueryTypes, LogsQueryValues } from "@/types/logs.d"
import type { User } from "@/types/user.d"
import { useResizeObserver } from "@vueuse/core"
import _orderBy from "lodash/orderBy"
import { NBadge, NButton, NEmpty, NModal, NPagination, NPopover, NSelect, NSpin, useMessage } from "naive-ui"
import { nanoid } from "nanoid"
import { computed, onBeforeMount, ref, toRefs } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { LogEventType } from "@/types/logs.d"
import LogItem from "./LogItem.vue"
import LogsFilters from "./LogsFilters.vue"

interface LogExt extends Log {
	id?: string
}

const props = defineProps<{ userId?: string }>()
const { userId } = toRefs(props)

const message = useMessage()
const loadingUsers = ref(false)
const loading = ref(false)
const loadingPurge = ref(false)
const showPurgeConfirm = ref(false)
const usersList = ref<User[]>([])
const logsList = ref<LogExt[]>([])
const showFilters = ref(false)

const pageSize = ref(25)
const currentPage = ref(1)
const simpleMode = ref(false)
const showSizePicker = ref(true)
const pageSizes = [10, 25, 50, 100]
const header = ref()
const pageSlot = ref(8)

const itemsPaginated = computed(() => {
	const from = (currentPage.value - 1) * pageSize.value
	const to = currentPage.value * pageSize.value

	const list = _orderBy(logsList.value, ["timestamp"], ["desc"])

	return list.slice(from, to)
})

const FilterIcon = "carbon:filter-edit"
const TrashIcon = "carbon:trash-can"
const InfoIcon = "carbon:information"

const total = computed<number>(() => {
	return logsList.value.length || 0
})

const eventInfoTotal = computed<number>(() => {
	return logsList.value.filter(o => o.event_type === LogEventType.INFO).length || 0
})
const eventErrorTotal = computed<number>(() => {
	return logsList.value.filter(o => o.event_type === LogEventType.ERROR).length || 0
})

const filterType = ref<LogsQueryTypes | null>(null)
const filterValue = ref<LogsQueryValues | null>(null)

const filtered = ref(false)

const purgeSelected = ref<LogsQueryTimeRange | "">("")
const purgeOptions: { label: string; value: LogsQueryTimeRange | string }[] = [
	{ label: "All Logs", value: "" },
	{ label: "1 Hour", value: "1h" },
	{ label: "6 Hours", value: "6h" },
	{ label: "12 Hours", value: "12h" },
	{ label: "1 Day", value: "1d" },
	{ label: "3 Days", value: "3d" },
	{ label: "1 Week", value: "1w" }
]

function purge() {
	loadingPurge.value = true

	Api.logs
		.purge(purgeSelected.value || undefined)
		.then(res => {
			if (res.data.success) {
				getData()
				message.success(res.data?.message || "Logs purged successfully")
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingPurge.value = false
		})
}

function getData() {
	showFilters.value = false
	loading.value = true

	const query =
		filterType.value && filterValue.value ? ({ [filterType.value]: filterValue.value } as LogsQuery) : undefined

	Api.logs
		.getLogs(query)
		.then(res => {
			if (res.data.success) {
				logsList.value = (res.data.logs || []).map((o: LogExt) => {
					o.id = nanoid()
					return o
				})
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			logsList.value = []

			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}

function getUsers() {
	loadingUsers.value = true

	Api.users
		.getUsers()
		.then(res => {
			if (res.data.success) {
				usersList.value = res.data?.users || []
			}
		})
		.finally(() => {
			loadingUsers.value = false
		})
}

useResizeObserver(header, entries => {
	const entry = entries[0]
	const { width } = entry.contentRect

	pageSlot.value = width < 700 ? 5 : 8
	simpleMode.value = width < 550
})

onBeforeMount(() => {
	if (userId.value) {
		filterType.value = "userId"
		filterValue.value = userId.value
		filtered.value = true
	}

	getUsers()
	getData()
})
</script>
