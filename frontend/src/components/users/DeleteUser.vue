<template>
	<n-button :size :type quaternary class="!w-full !justify-start" :loading @click="handleDelete()">
		<template #icon>
			<Icon :name="DeleteIcon" :size="14"></Icon>
		</template>
		Delete User
	</n-button>
</template>

<script setup lang="ts">
import type { User } from "@/types/user"
import type { Size, Type } from "naive-ui/es/button/src/interface"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { NButton, useDialog, useMessage } from "naive-ui"
import { computed, h, ref, watch } from "vue"

const {
	type = "error",
	size,
	user
} = defineProps<{
	user?: User
	size?: Size
	type?: Type
}>()

const emit = defineEmits<{
	(e: "success"): void
	(e: "loading", value: boolean): void
}>()

const DeleteIcon = "ph:trash"
const dialog = useDialog()
const message = useMessage()
const username = computed(() => user?.username || "")
const userId = computed(() => user?.id || 0)
const loading = ref(false)

function deleteCustomer() {
	loading.value = true

	Api.auth
		.delete(userId.value)
		.then(res => {
			if (res.data.success) {
				emit("success")
				message.success(res.data?.message || "User was successfully deleted.")
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

function handleDelete() {
	dialog.warning({
		title: "Confirm",
		content: () =>
			h("div", {
				innerHTML: `Are you sure you want to delete the User: <strong>${username.value}</strong> ?`
			}),
		positiveText: "Yes I'm sure",
		negativeText: "Cancel",
		onPositiveClick: () => {
			deleteCustomer()
		},
		onNegativeClick: () => {
			message.info("Delete canceled")
		}
	})
}

watch(loading, val => {
	emit("loading", val)
})
</script>
