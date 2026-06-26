<template>
	<Icon
		:name="loadingBookmark ? LoadingIcon : isBookmark ? StarActiveIcon : StarIcon"
		:size="16"
		class="hover:text-primary"
		:class="{ 'text-primary': isBookmark }"
		@click.stop="toggleBookmark()"
	/>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { SocAlert } from "@/types/soc/alert"
import { useMessage } from "naive-ui"
import { ref, toRefs } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"

const props = defineProps<{
	alert: SocAlert
	isBookmark?: boolean
}>()

const emit = defineEmits<{
	(e: "bookmark", value: boolean): void
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

		const method = isBookmark.value
			? Api.soc.removeAlertBookmark(alert.value.alert_id.toString())
			: Api.soc.addAlertBookmark(alert.value.alert_id.toString())

		method
			.then(res => {
				if (res.data.success) {
					emit("bookmark", !isBookmark.value)
					message.success(res.data?.message || "Stream started.")
				} else {
					message.warning(res.data?.message || "An error occurred. Please try again later.")
				}
			})
			.catch(err => {
				message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
			})
			.finally(() => {
				loadingBookmark.value = false
			})
	}
}
</script>
