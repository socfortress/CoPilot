<template>
	<div class="page">
		<div class="header-row mb-4 flex gap-2">
			<span>
				Total:
				<strong class="font-mono">{{ totalAlerts }}</strong>
			</span>
			<span>/</span>
			<span>
				Bookmarked:
				<strong class="font-mono">{{ bookmarksList.length }}</strong>
			</span>
		</div>
		<n-spin :show="loadingAlerts">
			<template v-if="list.length">
				<div class="list">
					<SocAlertItem
						v-for="alert of list"
						:key="alert.id"
						:alert="alert.item"
						class="mb-2"
						:is-bookmark="alert.isBookmark"
						@bookmark="switchAlert(alert.id, alert.isBookmark)"
					/>
				</div>
			</template>
			<template v-else>
				<n-empty description="No items found" class="justify-center h-48" v-if="!loading" />
			</template>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import { ref, onBeforeMount, computed } from "vue"
import { useMessage, NSpin, NEmpty } from "naive-ui"
import Api from "@/api"
import SocAlertItem from "@/components/soc/SocAlertItem.vue"
import type { SocAlert } from "@/types/soc/alert.d"
import _uniqBy from "lodash/uniqBy"

const message = useMessage()
const loadingBookmarks = ref(false)
const loadingAlerts = ref(false)
const bookmarksList = ref<SocAlert[]>([])
const alertsList = ref<SocAlert[]>([])

const list = computed(() => {
	const list = [
		...bookmarksList.value.map(o => ({ item: o, id: o.alert_id, isBookmark: true })),
		...alertsList.value.map(o => ({ item: o, id: o.alert_id, isBookmark: false }))
	]
	return _uniqBy(list, o => o.id)
})

const loading = computed<boolean>(() => {
	return loadingBookmarks.value || loadingAlerts.value
})

const totalAlerts = computed<number>(() => {
	return list.value.length || 0
})

function switchAlert(alertId: number, isBookmark: boolean) {
	const fromList = isBookmark ? bookmarksList : alertsList
	const toList = isBookmark ? alertsList : bookmarksList

	const alert = fromList.value.find(o => o.alert_id === alertId)
	fromList.value = fromList.value.filter(o => o.alert_id !== alertId)

	if (alert) {
		toList.value.push(alert)
	}

	load(true)
}

function getAlerts(silent?: boolean) {
	if (!silent) {
		loadingAlerts.value = true
	}

	Api.soc
		.getAlerts()
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

function getBookmarks(silent?: boolean) {
	if (!silent) {
		loadingBookmarks.value = true
	}

	Api.soc
		.getAlertsBookmark()
		.then(res => {
			if (res.data.success) {
				bookmarksList.value = res.data.bookmarked_alerts || []
			} else {
				message.error(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingBookmarks.value = false
		})
}

function load(silent?: boolean) {
	getAlerts(silent)
	getBookmarks(silent)
}

onBeforeMount(() => {
	load()
})
</script>

<style lang="scss" scoped>
.page {
	.list {
		container-type: inline-size;
		min-height: 200px;

		.soc-alert-item {
			animation: soc-alert-item-fade 0.3s forwards;
			opacity: 0;

			@for $i from 0 through 30 {
				&:nth-child(#{$i}) {
					animation-delay: $i * 0.05s;
				}
			}

			@keyframes soc-alert-item-fade {
				from {
					opacity: 0;
					transform: translateY(10px);
				}
				to {
					opacity: 1;
				}
			}
		}
	}
}
</style>
