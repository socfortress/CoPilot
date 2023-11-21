<template>
	<div class="page">
		<n-spin :show="loadingBookmarks">
			<div class="list bookmarks">
				<template v-if="bookmarksList.length">
					<SocAlertItem v-for="alert of bookmarksList" :key="alert.alert_id" :alert="alert" class="mb-2" />
				</template>
				<template v-else>
					<n-empty description="No items found" class="justify-center h-48" v-if="!loadingBookmarks" />
				</template>
			</div>
		</n-spin>
		<n-spin :show="loading">
			<div class="list my-3">
				<template v-if="alertsList.length">
					<SocAlertItem v-for="alert of alertsList" :key="alert.alert_id" :alert="alert" class="mb-2" />
				</template>
				<template v-else>
					<n-empty description="No items found" class="justify-center h-48" v-if="!loading" />
				</template>
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import { ref, onBeforeMount, computed } from "vue"
import { useMessage, NSpin, NEmpty } from "naive-ui"
import Api from "@/api"
import SocAlertItem from "@/components/soc/SocAlertItem.vue"
import type { SocAlert } from "@/types/soc/alert.d"

const message = useMessage()
const loadingBookmarks = ref(false)
const loading = ref(false)
const bookmarksList = ref<SocAlert[]>([])
const alertsList = ref<SocAlert[]>([])

const totalAlerts = computed<number>(() => {
	return alertsList.value.length || 0
})

function getAlerts() {
	loading.value = true

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
			loading.value = false
		})
}

function getBookmarks() {
	loadingBookmarks.value = true

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

onBeforeMount(() => {
	getAlerts()
	getBookmarks()
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
