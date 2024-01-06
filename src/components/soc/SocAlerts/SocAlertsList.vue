<template>
	<div class="soc-alerts-list">
		<div class="header flex items-center justify-end gap-2" ref="header">
			<PaginationIndeterminate v-model:page="page" v-model:pageSize="pageSize" :pageSizes="pageSizes" />

			<!--
				<n-select size="small" v-model:value="timerange" :options="timeOptions" class="!w-32" v-if="!compactMode" />
				<n-popover overlap v-if="compactMode" placement="right">
					<template #trigger>
						<div class="bg-color border-radius">
							<n-button size="small">
								<template #icon>
									<Icon :name="FilterIcon"></Icon>
								</template>
							</n-button>
						</div>
					</template>
					<div class="mb-2">
						<div class="text-secondary-color text-sm my-1">Time range:</div>
						<n-select size="small" v-model:value="timerange" :options="timeOptions" class="!w-32 mb-1" />
					</div>
				</n-popover>
			-->
		</div>

		<n-spin :show="loadingAlerts">
			<div class="list">
				<template v-if="alertsList.length">
					<SocAlertItem
						v-for="alert of alertsList"
						:key="alert.alert_id"
						:alertData="alert"
						class="item-appear item-appear-bottom item-appear-005 mb-2"
						:is-bookmark="isBookmarked(alert)"
						:users="usersList"
						:highlight="alert.alert_id.toString() === highlight"
						@bookmark="bookmark()"
					/>
				</template>
				<template v-else>
					<n-empty description="No items found" class="justify-center h-48" v-if="!loadingAlerts" />
				</template>
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import { ref, onBeforeMount, watch, toRefs, nextTick, onBeforeUnmount } from "vue"
import { useMessage, NSpin, NEmpty, NPagination, NSelect, NPopover, NButton, NInputNumber, NSplit } from "naive-ui"
import Api from "@/api"
import SocAlertItem from "./SocAlertItem.vue"
import type { SocAlert } from "@/types/soc/alert.d"
import type { SocUser } from "@/types/soc/user.d"
import type { AlertsFilter } from "@/api/soc"
import { useResizeObserver, watchDebounced } from "@vueuse/core"
import PaginationIndeterminate from "@/components/common/PaginationIndeterminate.vue"
import Icon from "@/components/common/Icon.vue"

const props = defineProps<{
	highlight: string | null | undefined
	bookmarksList?: SocAlert[]
	usersList?: SocUser[]
}>()
const { highlight, bookmarksList, usersList } = toRefs(props)

const emit = defineEmits<{
	(e: "bookmark"): void
}>()

const message = useMessage()
const loadingAlerts = ref(false)
const alertsList = ref<SocAlert[]>([])

const pageSize = ref(50)
const pageSizes = [25, 50, 100, 150, 200]
const page = ref(1)
const sort = ref<"desc" | "asc">("desc")
const alertTitle = ref("")
const header = ref()
const compactMode = ref(false)

let abortController: AbortController | null = null

function isBookmarked(alert: SocAlert): boolean {
	return !!(bookmarksList.value || []).filter(o => o.alert_id === alert.alert_id).length
}

function bookmark() {
	emit("bookmark")
	getAlerts()
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
				alertsList.value = res.data?.alerts || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingAlerts.value = false
		})
}

function scrollToAlert(id: string) {
	const element = document.getElementById(`alert-${id}`)
	const scrollContent = document.querySelector("#main > .n-scrollbar > .n-scrollbar-container") as HTMLElement

	if (element && scrollContent) {
		const wrap: HTMLElement = scrollContent
		const middle = element.offsetTop - wrap.offsetHeight / 2
		scrollContent?.scrollTo({ top: middle, behavior: "smooth" })
	}
}

watch(loadingAlerts, val => {
	if (!val) {
		nextTick(() => {
			setTimeout(() => {
				if (highlight.value) {
					scrollToAlert(highlight.value)
				}
			}, 300)
		})
	}
})

watch(highlight, val => {
	if (val) {
		nextTick(() => {
			setTimeout(() => {
				scrollToAlert(val)
			})
		})
	}
})

watchDebounced(
	[page, pageSize],
	(a, b, c) => {
		abortController?.abort()

		setTimeout(() => {
			getAlerts()
		}, 200)
	},
	{ debounce: 500 }
)

useResizeObserver(header, entries => {
	const entry = entries[0]
	const { width } = entry.contentRect

	if (width < 650) {
		compactMode.value = true
		pageSize.value = pageSizes[0]
	} else {
		compactMode.value = false
	}
})

onBeforeMount(() => {
	getAlerts()
})

onBeforeUnmount(() => {
	abortController?.abort()
})
</script>

<style lang="scss" scoped>
.soc-alerts-list {
	.list {
		container-type: inline-size;
		min-height: 200px;
	}
}
</style>
