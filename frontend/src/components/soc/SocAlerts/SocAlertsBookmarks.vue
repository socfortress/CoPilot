<template>
	<div class="soc-alerts-bookmarks">
		<div class="header flex items-center">
			<div class="info">
				Bookmarked:
				<code>
					<strong>{{ bookmarksList.length }}</strong>
				</code>
			</div>
		</div>

		<n-spin :show="loadingBookmarks">
			<div class="list">
				<template v-if="bookmarksList.length">
					<SocAlertItem
						v-for="alert of bookmarksList"
						:key="alert.alert_id"
						:alertData="alert"
						class="item-appear item-appear-bottom item-appear-005 mb-2"
						:is-bookmark="true"
						:users="usersList"
						@bookmark="bookmark()"
						@deleted="itemDeleted(alert.alert_id)"
					/>
				</template>
				<template v-else>
					<n-empty description="No items found" class="justify-center h-48" v-if="!loadingBookmarks" />
				</template>
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import { ref, onBeforeMount, toRefs, onMounted, onBeforeUnmount } from "vue"
import { useMessage, NSpin, NEmpty } from "naive-ui"
import Api from "@/api"
import SocAlertItem from "./SocAlertItem/SocAlertItem.vue"
import type { SocAlert } from "@/types/soc/alert.d"
import type { SocUser } from "@/types/soc/user.d"
import axios from "axios"

const props = defineProps<{
	usersList?: SocUser[]
}>()
const { usersList } = toRefs(props)

const emit = defineEmits<{
	(e: "bookmark"): void
	(e: "deleted", value?: string): void
	(e: "loaded", value: SocAlert[]): void
	(
		e: "mounted",
		value: {
			reload: () => void
		}
	): void
}>()

let reloadTimeout: NodeJS.Timeout | null = null
const message = useMessage()
const loadingBookmarks = ref(false)
const bookmarksList = ref<SocAlert[]>([])

let abortController: AbortController | null = null

function bookmark() {
	emit("bookmark")
	safeReload()
}

function getBookmarks() {
	loadingBookmarks.value = true

	abortController = new AbortController()

	Api.soc
		.getAlertsBookmark(abortController.signal)
		.then(res => {
			if (res.data.success) {
				bookmarksList.value = res.data.bookmarked_alerts || []
				emit("loaded", bookmarksList.value)
			} else {
				message.error(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			if (!axios.isCancel(err)) {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			}
		})
		.finally(() => {
			loadingBookmarks.value = false
		})
}

function safeReload() {
	abortController?.abort()

	if (reloadTimeout) {
		clearTimeout(reloadTimeout)
	}

	reloadTimeout = setTimeout(() => {
		getBookmarks()
	}, 200)
}

function itemDeleted(alertId: string | number) {
	getBookmarks()
	emit("deleted", alertId.toString())
}

onBeforeMount(() => {
	getBookmarks()
})

onMounted(() => {
	emit("mounted", {
		reload: () => {
			safeReload()
		}
	})
})

onBeforeUnmount(() => {
	abortController?.abort()
})
</script>

<style lang="scss" scoped>
.soc-alerts-bookmarks {
	.header {
		height: 50px;
	}
	.list {
		container-type: inline-size;
		min-height: 200px;
	}
}
</style>
