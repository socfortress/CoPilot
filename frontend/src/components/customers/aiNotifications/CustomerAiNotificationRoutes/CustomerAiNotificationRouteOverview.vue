<template>
	<div class="flex flex-col">
		<n-spin :show="loadingDelete || loadingDetails">
			<div v-if="editing && resolvedEntity" class="flex flex-col gap-4" :class="fullWidth ? 'p-0' : 'p-6'">
				<CustomerAiNotificationRouteForm
					:customer-code
					:editing-route="resolvedEntity"
					:scope
					@submitted="onSubmitted()"
					@close="editing = false"
				/>
			</div>
			<CustomerAiNotificationRouteDetails
				v-else-if="resolvedEntity"
				:entity="resolvedEntity"
				:customer-code
				:scope
				:full-width
				@toggled="emit('updated')"
			/>
			<div v-else-if="!loadingDetails" class="min-h-40"></div>
		</n-spin>

		<div
			v-if="!editing && resolvedEntity"
			class="flex flex-wrap items-center justify-end gap-4"
			:class="fullWidth ? 'pt-4' : 'p-6'"
		>
			<n-button text type="error" ghost :loading="loadingDelete" @click="handleDelete">
				<template #icon>
					<Icon :name="DeleteIcon" :size="15" />
				</template>
				Delete
			</n-button>
			<n-button :disabled="loadingDelete" @click="editing = true">
				<template #icon>
					<Icon :name="EditIcon" :size="14" />
				</template>
				Edit
			</n-button>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { NotificationRoute, NotificationScope } from "@/types/notifications"
import { NButton, NSpin, useDialog, useMessage } from "naive-ui"
import { computed, h, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useEntityDetails } from "@/composables/useEntityDetails"
import { getApiErrorMessage } from "@/utils"
import CustomerAiNotificationRouteDetails from "./CustomerAiNotificationRouteDetails.vue"
import CustomerAiNotificationRouteForm from "./CustomerAiNotificationRouteForm.vue"

// Mounted both inside a list (the row already holds the route) and on an
// internal route's own page, where only the id is known. Only internal routes
// are fetchable by id — a customer route is always handed down, since its
// endpoint needs the tenant code that the id alone doesn't carry.

const {
	entity,
	routeId,
	customerCode,
	scope,
	fullWidth = false
} = defineProps<{
	entity?: NotificationRoute
	routeId?: number
	customerCode?: string
	scope?: NotificationScope
	fullWidth?: boolean
}>()

const emit = defineEmits<{
	(e: "loaded", value: NotificationRoute): void
	(e: "deleted"): void
	(e: "updated"): void
}>()

const DeleteIcon = "ph:trash"
const EditIcon = "uil:edit-alt"

const message = useMessage()
const dialog = useDialog()
const loadingDelete = ref(false)
const editing = ref(false)

const isInternalScope = computed(() => scope === "internal" || !customerCode)

const {
	loading: loadingDetails,
	entity: resolvedEntity,
	reload
} = useEntityDetails<NotificationRoute, number>({
	entity: () => entity,
	id: () => routeId,
	fetch: id =>
		Api.notifications.getInternalRoute(id).then(res => ({
			entity: res.data.success ? (res.data.route ?? null) : null,
			message: res.data.message
		})),
	notFoundMessage: "Internal route not found.",
	errorMessage: "Could not load the route.",
	onLoaded: value => emit("loaded", value)
})

// The form reports success without the saved row, so the detail page refetches.
// In a list the row is owned by the parent, which refreshes on `updated`.
function onSubmitted() {
	editing.value = false
	reload()
	emit("updated")
}

function deleteRoute() {
	if (!resolvedEntity.value) return

	loadingDelete.value = true

	const request = isInternalScope.value
		? Api.notifications.deleteInternalRoute(resolvedEntity.value.id)
		: Api.notifications.deleteRoute(customerCode as string, resolvedEntity.value.id)

	request
		.then(res => {
			if (res.data.success) {
				message.success("Route deleted")
				emit("deleted")
			} else {
				message.warning(res.data.message || "Failed to delete route")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "Failed to delete route")
		})
		.finally(() => {
			loadingDelete.value = false
		})
}

function handleDelete() {
	if (!resolvedEntity.value) return

	dialog.warning({
		title: "Confirm",
		content: () =>
			h("div", {
				innerHTML:
					`Delete the route <strong>${resolvedEntity.value?.name}</strong>? ` +
					`Dispatch log entries will be retained.`
			}),
		positiveText: "Yes I'm sure",
		negativeText: "Cancel",
		onPositiveClick: () => {
			deleteRoute()
		},
		onNegativeClick: () => {
			message.info("Delete canceled")
		}
	})
}
</script>
