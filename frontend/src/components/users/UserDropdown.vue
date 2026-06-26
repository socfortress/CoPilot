<template>
	<n-dropdown
		trigger="click"
		to="body"
		:options
		display-directive="show"
		placement="left-start"
		:keyboard="false"
		class="min-w-60"
	>
		<n-button text>
			<template #icon>
				<Icon :name="DropdownIcon" :size="24" />
			</template>
		</n-button>
	</n-dropdown>
</template>

<script setup lang="ts">
import type { User } from "@/types/user"
import { NButton, NDropdown } from "naive-ui"
import { computed, defineAsyncComponent, h } from "vue"
import Icon from "@/components/common/Icon.vue"

const props = defineProps<{
	user: User
}>()

const emit = defineEmits<{
	success: []
	loading: [value: boolean]
}>()

const AssignRole = defineAsyncComponent(() => import("./AssignRole.vue"))
const AssignCustomer = defineAsyncComponent(() => import("./AssignCustomer.vue"))
const AssignTags = defineAsyncComponent(() => import("./AssignTags.vue"))
const ChangePassword = defineAsyncComponent(() => import("./ChangePassword.vue"))
const DeleteUser = defineAsyncComponent(() => import("./DeleteUser.vue"))

const DropdownIcon = "carbon:overflow-menu-horizontal"

const options = computed(() => [
	{
		key: "AssignRole",
		type: "render",
		render: () =>
			h(AssignRole, {
				user: props.user,
				onSuccess: () => emit("success")
			})
	},
	{
		key: "AssignCustomer",
		type: "render",
		render: () =>
			h(AssignCustomer, {
				user: props.user,
				onSuccess: () => emit("success")
			})
	},
	{
		key: "AssignTags",
		type: "render",
		render: () =>
			h(AssignTags, {
				user: props.user,
				onSuccess: () => emit("success")
			})
	},
	{
		key: "ChangePassword",
		type: "render",
		render: () =>
			h(ChangePassword, {
				user: props.user,
				quaternary: true,
				className: "w-full! justify-start!"
			})
	},
	{
		key: "DeleteUser",
		type: "render",
		render: () =>
			h(DeleteUser, {
				user: props.user,
				onSuccess: () => emit("success"),
				onLoading: (value: boolean) => emit("loading", value)
			})
	}
])
</script>
