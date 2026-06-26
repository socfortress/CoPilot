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
			<div class="min-h-52">
				<template v-if="bookmarksList.length">
					<SocAlertItem
						v-for="alert of bookmarksList"
						:key="alert.alert_id"
						:alert-data="alert"
						class="item-appear item-appear-bottom item-appear-005 mb-2"
						is-bookmark
						:users="usersList"
						@bookmark="bookmark()"
						@deleted="itemDeleted(alert.alert_id)"
					/>
				</template>
				<template v-else>
					<n-empty v-if="!loadingBookmarks" description="No items found" class="h-48 justify-center" />
				</template>
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { SocAlert } from "@/types/soc/alert"
import type { SocUser } from "@/types/soc/user"
import axios from "axios"
import { NEmpty, NSpin, useMessage } from "naive-ui"
import { onBeforeMount, onBeforeUnmount, ref, toRefs } from "vue"
import Api from "@/api"
import { getApiErrorMessage } from "@/utils"
import SocAlertItem from "./SocAlertItem/SocAlertItem.vue"

const props = defineProps<{
	usersList?: SocUser[]
}>()
const emit = defineEmits<{
	(e: "bookmark"): void
	(e: "deleted", value?: string): void
	(e: "loaded", value: SocAlert[]): void
}>()

const { usersList } = toRefs(props)

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
				message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
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

defineExpose({ reload: safeReload })

onBeforeUnmount(() => {
	abortController?.abort()
})
</script>

<style lang="scss" scoped>
.soc-alerts-bookmarks {
	.header {
		height: 50px;
	}
}
</style>
