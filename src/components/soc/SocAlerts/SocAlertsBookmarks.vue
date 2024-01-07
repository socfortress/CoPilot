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
import { ref, onBeforeMount, toRefs, onMounted } from "vue"
import { useMessage, NSpin, NEmpty } from "naive-ui"
import Api from "@/api"
import SocAlertItem from "./SocAlertItem.vue"
import type { SocAlert } from "@/types/soc/alert.d"
import type { SocUser } from "@/types/soc/user.d"

const props = defineProps<{
	usersList?: SocUser[]
}>()
const { usersList } = toRefs(props)

const emit = defineEmits<{
	(e: "bookmark"): void
	(e: "loaded", value: SocAlert[]): void
	(
		e: "mounted",
		value: {
			reload: () => void
		}
	): void
}>()

const message = useMessage()
const loadingBookmarks = ref(false)
const bookmarksList = ref<SocAlert[]>([])

function bookmark() {
	emit("bookmark")
	getBookmarks()
}

function getBookmarks() {
	loadingBookmarks.value = true

	Api.soc
		.getAlertsBookmark()
		.then(res => {
			if (res.data.success) {
				bookmarksList.value = res.data.bookmarked_alerts || []
				emit("loaded", bookmarksList.value)
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
	getBookmarks()
})

onMounted(() => {
	emit("mounted", {
		reload: () => {
			getBookmarks()
		}
	})
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
