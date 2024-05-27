<template>
	<Icon
		:name="loadingBookmark ? LoadingIcon : isBookmark ? StarActiveIcon : StarIcon"
		:size="16"
		@click="toggleBookmark()"
		class="toggler-bookmark"
		:class="{ active: isBookmark }"
	></Icon>
</template>

<script setup lang="ts">
import type { SocAlert } from "@/types/soc/alert.d"
import Icon from "@/components/common/Icon.vue"
import { ref, toRefs } from "vue"
import Api from "@/api"
import { useMessage } from "naive-ui"

const emit = defineEmits<{
	(e: "bookmark", value: boolean): void
}>()

const props = defineProps<{
	alert: SocAlert
	isBookmark?: boolean
}>()
const { alert, isBookmark } = toRefs(props)

const StarActiveIcon = "carbon:star-filled"
const StarIcon = "carbon:star"
const LoadingIcon = "eos-icons:loading"

const loadingBookmark = ref(false)
const message = useMessage()

function toggleBookmark() {
	if (alert.value?.alert_id) {
		loadingBookmark.value = true

		const method = isBookmark.value ? "removeAlertBookmark" : "addAlertBookmark"

		Api.soc[method](alert.value.alert_id.toString())
			.then(res => {
				if (res.data.success) {
					emit("bookmark", method === "removeAlertBookmark" ? false : true)
					message.success(res.data?.message || "Stream started.")
				} else {
					message.warning(res.data?.message || "An error occurred. Please try again later.")
				}
			})
			.catch(err => {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			})
			.finally(() => {
				loadingBookmark.value = false
			})
	}
}
</script>

<style lang="scss" scoped>
.toggler-bookmark {
	&.active {
		color: var(--primary-color);
	}
	&:hover {
		color: var(--primary-color);
	}
}
</style>
