<template>
	<div class="soc-alerts-list">
		<div ref="header" class="flex h-14 items-center justify-end gap-2">
			<slot name="header"></slot>
			<div class="grow">
				<n-input v-model:value="alertTitle" size="small" placeholder="Search by title..." clearable />
			</div>
			<div class="delete-box">
				<n-popover v-if="checkedCount" :width="200" placement="bottom" style="max-height: 240px" scrollable>
					<template #trigger>
						<n-button
							size="small"
							type="error"
							ghost
							:loading="loadingPurge"
							:disabled="loadingAlerts"
							@click="handleDelete()"
						>
							<div class="flex items-center gap-2">
								<Icon :name="TrashIcon" :size="16" />
								<span class="flex items-center gap-2">
									<span v-if="!compactMode">Delete Alerts:</span>
									<span class="font-mono">
										{{ checkedCount }}
									</span>
								</span>
							</div>
						</n-button>
					</template>
					<template #header>Selected Alerts</template>
					<template #footer>
						<div class="flex justify-end">
							<n-button size="tiny" @click="clearChecked()">Clear selection</n-button>
						</div>
					</template>
					<div class="checked-list flex flex-col gap-2">
						<div v-for="alertId of checkedList" :key="alertId" class="w-full">
							<n-button size="small" class="!w-full !justify-start" @click="clearChecked(alertId)">
								<template #icon>
									<Icon :name="CloseIcon" :size="18" />
								</template>
								<span class="font-mono">#{{ alertId }}</span>
							</n-button>
						</div>
					</div>
				</n-popover>
				<n-button v-else size="small" type="error" ghost :loading="loadingPurge" @click="handlePurge()">
					<div class="flex items-center gap-2">
						<Icon :name="TrashIcon" :size="16" />
						<span class="xs:block hidden">Purge</span>
					</div>
				</n-button>
			</div>
			<PaginationIndeterminate
				v-model:page="page"
				v-model:page-size="pageSize"
				v-model:sort="sort"
				:page-sizes="pageSizes"
				:show-page-sizes="!compactMode"
				:show-sort="!smallDeviceMode"
			/>
		</div>

		<n-spin :show="loadingAlerts || loadingPurge">
			<div class="min-h-52">
				<template v-if="alertsList.length">
					<SocAlertItem
						v-for="alert of alertsList"
						:key="alert.id"
						v-model:checked="alert.checked"
						:alert-data="alert.data"
						class="item-appear item-appear-bottom item-appear-005 mb-2"
						:is-bookmark="isBookmarked(alert.data)"
						:users="usersList"
						:highlight="alert.id === highlight"
						show-badges-toggle
						show-checkbox
						@check="toggleCheckedList(alert.id, $event)"
						@bookmark="bookmark()"
						@deleted="itemDeleted(alert.id)"
					/>
				</template>
				<template v-else>
					<n-empty v-if="!loadingAlerts" description="No items found" class="h-48 justify-center" />
				</template>
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { AlertsFilter } from "@/api/endpoints/soc"
import type { SocAlert } from "@/types/soc/alert.d"
import type { SocUser } from "@/types/soc/user.d"
import { useResizeObserver, watchDebounced } from "@vueuse/core"
import axios from "axios"
import { NButton, NEmpty, NInput, NPopover, NSpin, useDialog, useMessage } from "naive-ui"
import { computed, nextTick, onBeforeMount, onBeforeUnmount, onMounted, ref, toRefs, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import PaginationIndeterminate from "@/components/common/PaginationIndeterminate.vue"
import SocAlertItem from "./SocAlertItem/SocAlertItem.vue"
// MOCK
// import { alerts as alertsMock } from "./mock"

const props = defineProps<{
	highlight: string | null | undefined
	bookmarksList?: SocAlert[]
	usersList?: SocUser[]
}>()
const emit = defineEmits<{
	(e: "bookmark"): void
	(e: "deleted", value?: string): void
	(
		e: "mounted",
		value: {
			reload: () => void
			itemDeleted: (alertId: string, noEmit?: boolean) => void
		}
	): void
}>()

const { highlight, bookmarksList, usersList } = toRefs(props)

const TrashIcon = "carbon:trash-can"
const CloseIcon = "carbon:close"

let reloadTimeout: NodeJS.Timeout | null = null
const dialog = useDialog()
const message = useMessage()
const loadingPurge = ref(false)
const loadingAlerts = ref(false)
const alertsList = ref<{ checked: boolean; id: string; data: SocAlert }[]>([])
const checkedList = ref<string[]>([])

const pageSize = ref(50)
const pageSizes = [25, 50, 100, 150, 200]
const page = ref(1)
const sort = ref<"desc" | "asc">("desc")
const alertTitle = ref("")
const header = ref()
const compactMode = ref(false)
const smallDeviceMode = ref(false)

let abortController: AbortController | null = null

const checkedCount = computed(() => checkedList.value.length)

function isBookmarked(alert: SocAlert): boolean {
	return !!(bookmarksList.value || []).filter(o => o.alert_id === alert.alert_id).length
}

function bookmark() {
	emit("bookmark")
	safeReload()
}

function getAlerts() {
	loadingAlerts.value = true

	abortController = new AbortController()

	const filter: Partial<AlertsFilter> = {}
	if (pageSize.value) {
		filter.pageSize = pageSize.value
	}
	if (page.value) {
		filter.page = page.value
	}
	if (sort.value) {
		filter.sort = sort.value
	}
	if (alertTitle.value) {
		filter.alertTitle = alertTitle.value
	}

	Api.soc
		.getAlerts(filter, abortController.signal)
		.then(res => {
			if (res.data.success) {
				alertsList.value = (res.data?.alerts || []).map(o => ({
					checked: isChecked(o.alert_id.toString()),
					data: o,
					id: o.alert_id.toString()
				}))
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			if (!axios.isCancel(err)) {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			}
		})
		.finally(() => {
			loadingAlerts.value = false
		})
}

function scrollToItem(id: string) {
	const element = document.getElementById(`alert-${id}`)
	const scrollContent = document.querySelector("#main > .n-scrollbar > .n-scrollbar-container") as HTMLElement

	if (element && scrollContent) {
		const wrap: HTMLElement = scrollContent
		const middle = element.offsetTop - wrap.offsetHeight / 2
		scrollContent?.scrollTo({ top: middle, behavior: "smooth" })
	}
}

function safeReload() {
	abortController?.abort()

	if (reloadTimeout) {
		clearTimeout(reloadTimeout)
	}

	reloadTimeout = setTimeout(() => {
		getAlerts()
	}, 200)
}

function handleDelete() {
	dialog.warning({
		title: "Confirm",
		content: "This will remove latest 1000 Soc Alerts, are you sure you want to proceed?",
		positiveText: "Yes I'm sure",
		negativeText: "Cancel",
		onPositiveClick: () => {
			deleteMultipleAlerts()
		},
		onNegativeClick: () => {
			message.info("Purge canceled")
		}
	})
}

function handlePurge() {
	dialog.warning({
		title: "Confirm",
		content: "This will remove 1000 Soc Alerts, are you sure you want to proceed?",
		positiveText: "Yes I'm sure",
		negativeText: "Cancel",
		onPositiveClick: () => {
			purge()
		},
		onNegativeClick: () => {
			message.info("Purge canceled")
		}
	})
}

function deleteMultipleAlerts() {
	loadingPurge.value = true

	Api.soc
		.deleteMultipleAlerts(checkedList.value)
		.then(res => {
			if (res.data.success) {
				clearChecked()
				getAlerts()
				emit("deleted")
				message.success(res.data?.message || "SOC Alerts purged successfully")
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

function purge() {
	loadingPurge.value = true

	Api.soc
		.purgeAlerts()
		.then(res => {
			if (res.data.success) {
				getAlerts()
				emit("deleted")
				message.success(res.data?.message || "SOC Alerts purged successfully")
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

function itemDeleted(alertId: string, noEmit = false) {
	clearChecked(alertId)
	getAlerts()
	if (!noEmit) {
		emit("deleted", alertId)
	}
}

function toggleCheckedList(alertId: string, value: boolean) {
	if (value) {
		checkedList.value.push(alertId)
	} else {
		checkedList.value = checkedList.value.filter(o => o !== alertId)
	}
}

function isChecked(alertId: string) {
	return checkedList.value.filter(o => o === alertId).length !== 0
}

function clearChecked(alertId?: string) {
	if (alertId) {
		const alert = alertsList.value.find(o => o.id === alertId)
		if (alert) {
			alert.checked = false
		}
		checkedList.value = checkedList.value.filter(o => o !== alertId)
	} else {
		for (const alert of alertsList.value) {
			alert.checked = false
		}
		checkedList.value = []
	}
}

watch(loadingAlerts, val => {
	if (!val) {
		nextTick(() => {
			setTimeout(() => {
				if (highlight.value) {
					scrollToItem(highlight.value)
				}
			}, 300)
		})
	}
})

watch(highlight, val => {
	if (val) {
		nextTick(() => {
			setTimeout(() => {
				scrollToItem(val)
			})
		})
	}
})

watchDebounced(
	[page, pageSize, sort, alertTitle],
	() => {
		safeReload()
	},
	{ debounce: 300 }
)

useResizeObserver(header, entries => {
	const entry = entries[0]
	const { width } = entry.contentRect

	if (width < 600) {
		compactMode.value = true
		pageSize.value = pageSizes[0]
	} else {
		compactMode.value = false
	}

	smallDeviceMode.value = width < 450
})

onBeforeMount(() => {
	// MOCK
	// alertsList.value = alertsMock as unknown as SocAlert[]
	getAlerts()
})

onMounted(() => {
	emit("mounted", {
		reload: () => {
			safeReload()
		},
		itemDeleted
	})
})

onBeforeUnmount(() => {
	abortController?.abort()
})
</script>
