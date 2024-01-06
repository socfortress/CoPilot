<template>
	<div class="soc-alerts-bookmarks">
		<div class="header flex items-center">
			<div class="info grow flex gap-5">
				<n-popover overlap placement="bottom-start">
					<template #trigger>
						<div class="bg-color border-radius">
							<n-button size="small" class="!cursor-help">
								<template #icon>
									<Icon :name="InfoIcon"></Icon>
								</template>
							</n-button>
						</div>
					</template>
					<div class="flex flex-col gap-2">
						<div class="box">
							Bookmarked:
							<code>{{ bookmarksList.length }}</code>
						</div>
					</div>
				</n-popover>
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
import { ref, onBeforeMount, toRefs } from "vue"
import { useMessage, NSpin, NEmpty, NPopover, NButton } from "naive-ui"
import Api from "@/api"
import SocAlertItem from "./SocAlertItem.vue"
import type { SocAlert } from "@/types/soc/alert.d"
import type { SocUser } from "@/types/soc/user.d"
import Icon from "@/components/common/Icon.vue"

const props = defineProps<{
	usersList?: SocUser[]
}>()
const { usersList } = toRefs(props)

const emit = defineEmits<{
	(e: "bookmark"): void
	(e: "loaded", value: SocAlert[]): void
}>()

const InfoIcon = "carbon:information"

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
</script>

<style lang="scss" scoped>
.soc-alerts-bookmarks {
	.list {
		container-type: inline-size;
		min-height: 200px;
	}
}
</style>
