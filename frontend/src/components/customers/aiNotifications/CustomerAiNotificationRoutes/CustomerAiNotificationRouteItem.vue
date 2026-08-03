<template>
	<div>
		<CardEntity hoverable embedded footer-box-class="items-center!">
			<template #headerMain>
				<div class="flex items-center gap-2">
					<Icon :name="channelIcon" :size="16" />
					<span class="font-medium">{{ route.name }}</span>
				</div>
			</template>

			<template #headerExtra>
				<n-button
					size="small"
					secondary
					:type="route.enabled ? 'warning' : 'success'"
					:loading="loadingToggle"
					@click="toggleEnabled"
				>
					<template #icon>
						<Icon :name="route.enabled ? PauseIcon : PlayIcon" />
					</template>
					{{ route.enabled ? "Disable" : "Enable" }}
				</n-button>
			</template>

			<template #default>
				<div class="flex flex-col gap-3 text-sm">
					<div class="flex flex-col gap-0.5 text-sm">
						<!--
							Only Shuffle keeps its target in `destination`; every other
							channel keeps it in the provider's `config`, which is why this
							goes through one resolver instead of reading the column.
						-->
						<div class="flex flex-wrap gap-1">
							<span class="font-medium">{{ destination.label }}:</span>
							<span v-if="destination.values.length" class="flex flex-wrap gap-1">
								<code v-for="value in destination.values" :key="value">{{ value }}</code>
							</span>
							<span v-else class="text-secondary italic">{{ destination.note }}</span>
						</div>
						<div v-if="isWebhook && hasCustomHeaders" class="flex flex-wrap gap-1">
							<span class="font-medium">Custom headers:</span>
							<span class="italic">configured</span>
						</div>
						<div v-if="isWebhook && webhookConfig.include_full_report" class="flex flex-wrap gap-1">
							<span class="font-medium">Full AI report:</span>
							<span class="italic">included</span>
						</div>
						<div v-if="route.format_template" class="flex flex-wrap gap-1">
							<span class="font-medium">Custom template:</span>
							<span class="italic">configured</span>
						</div>
					</div>
					<div class="flex flex-wrap items-center gap-2">
						<Badge type="splitted" :color="severityColor" size="small">
							<template #label>Min severity</template>
							<template #value>{{ route.min_severity }}</template>
						</Badge>
						<Badge type="splitted" size="small">
							<template #label>Channel</template>
							<template #value>{{ channelLabel }}</template>
						</Badge>
					</div>
				</div>
			</template>

			<template #footerMain>
				<div class="flex flex-wrap items-center gap-2">
					<Badge type="splitted">
						<template #label>dispatch</template>
						<template #value>{{ route.dispatch_count }}</template>
					</Badge>

					<Badge type="splitted">
						<template #label>fired</template>
						<template v-if="route.last_dispatched_at" #value>
							{{ formatDate(route.last_dispatched_at, dFormats.datetime) }}
						</template>
						<template v-else #value>never fired</template>
					</Badge>

					<Badge v-if="route.created_by" type="splitted">
						<template #label>owner</template>
						<template #value>{{ route.created_by }}</template>
					</Badge>
				</div>
			</template>

			<template #footerExtra>
				<div class="flex items-center justify-end gap-2">
					<n-button size="tiny" quaternary @click="$emit('edit')">
						<template #icon>
							<Icon :name="EditIcon" :size="14" />
						</template>
						Edit
					</n-button>

					<n-popconfirm to="body" @positive-click="confirmDelete">
						<template #trigger>
							<n-button size="tiny" quaternary :loading="loadingDelete">
								<template #icon>
									<Icon :name="DeleteIcon" :size="14" />
								</template>
								Delete
							</n-button>
						</template>
						Delete this route? Dispatch log entries will be retained.
					</n-popconfirm>

					<!--
						Only internal routes have a page of their own: a customer route
						is reached through its customer, and its endpoint needs the
						tenant code that a bare id doesn't carry.
					-->
					<EntityDetailsButton
						size="tiny"
						:order="isInternalScope ? ['view', 'open'] : ['view']"
						:route="routeInternalNotificationRoute(route.id)"
						@view="showDetails = true"
					/>
				</div>
			</template>
		</CardEntity>

		<n-modal
			v-model:show="showDetails"
			:style="{ maxWidth: 'min(850px, 90vw)', minHeight: 'min(480px, 90vh)', overflow: 'hidden' }"
			display-directive="show"
		>
			<n-card
				content-class="flex flex-col p-0!"
				:title="`#${route.id} • ${route.name}`"
				closable
				:bordered="false"
				segmented
				role="modal"
				@close="showDetails = false"
			>
				<CustomerAiNotificationRouteOverview
					:entity="route"
					:customer-code
					:scope
					@updated="$emit('toggled')"
					@deleted="handleDeleted()"
				/>
			</n-card>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { NotificationRoute, NotificationScope, WebhookChannelConfig } from "@/types/notifications"
import { NButton, NCard, NModal, NPopconfirm, useMessage } from "naive-ui"
import { computed, ref } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import EntityDetailsButton from "@/components/common/EntityDetailsButton.vue"
import Icon from "@/components/common/Icon.vue"
import { useNavigation } from "@/composables/useNavigation"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"
import CustomerAiNotificationRouteOverview from "./CustomerAiNotificationRouteOverview.vue"
import { describeRouteDestination } from "./destination"

const props = defineProps<{
	route: NotificationRoute
	// Passed down rather than read off the route: `customer_code` is nullable
	// (internal routes belong to no tenant) while the customer-scoped API paths
	// need a concrete code. Absent for internal routes, which use their own
	// endpoints below.
	customerCode?: string
	scope?: NotificationScope
}>()

const emit = defineEmits<{
	(e: "edit"): void
	(e: "deleted"): void
	(e: "toggled"): void
}>()

const EditIcon = "carbon:edit"
const DeleteIcon = "carbon:trash-can"
const PauseIcon = "carbon:pause"
const PlayIcon = "carbon:play"

const loadingToggle = ref(false)
const loadingDelete = ref(false)
const showDetails = ref(false)
const message = useMessage()
const dFormats = useSettingsStore().dateFormat
const { routeInternalNotificationRoute } = useNavigation()

const isInternalScope = computed(() => props.scope === "internal")

const isWebhook = computed(() => props.route.channel === "webhook")

// Channel settings now live in the route's JSON `config`. Read through a typed
// view rather than casting at each use site — and tolerate a missing config,
// since the read schema deliberately returns {} for an unparseable row so a bad
// route stays visible in the list instead of 500-ing the page.
const webhookConfig = computed<WebhookChannelConfig>(() => (props.route.config ?? {}) as WebhookChannelConfig)
const hasCustomHeaders = computed(() => Object.keys(webhookConfig.value.headers ?? {}).length > 0)

const destination = computed(() => describeRouteDestination(props.route))

// Shuffle routes cache the app name on the row at form-submit time so we
// can render "Shuffle · Slack" without a roundtrip; webhook routes show
// the URL host so the list is scannable at a glance.
const channelIcon = computed(() => (isWebhook.value ? "carbon:webhook" : "carbon:integration"))
const channelLabel = computed(() => {
	if (isWebhook.value) {
		try {
			return `Webhook · ${new URL((props.route.config?.url as string) ?? "").host}`
		} catch {
			return "Webhook"
		}
	}
	const appName = props.route.config?.app_name as string | undefined
	return appName ? `Shuffle · ${appName}` : "Shuffle"
})

const severityColor = computed<"danger" | "warning" | "success">(() => {
	if (props.route.min_severity === "Critical" || props.route.min_severity === "High") return "danger"
	if (props.route.min_severity === "Medium") return "warning"
	return "success"
})

function handleDeleted() {
	showDetails.value = false
	emit("deleted")
}

async function toggleEnabled() {
	loadingToggle.value = true

	try {
		const payload = { enabled: !props.route.enabled }
		const code = props.customerCode
		const res =
			isInternalScope.value || !code
				? await Api.notifications.updateInternalRoute(props.route.id, payload)
				: await Api.notifications.updateRoute(code, props.route.id, payload)
		if (res.data.success) {
			message.success(`Route ${res.data.route.enabled ? "enabled" : "disabled"}`)
			emit("toggled")
		} else {
			message.warning(res.data.message || "Failed to toggle route")
		}
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "Failed to toggle route")
	} finally {
		loadingToggle.value = false
	}
}

async function confirmDelete() {
	loadingDelete.value = true

	try {
		const code = props.customerCode
		const res =
			isInternalScope.value || !code
				? await Api.notifications.deleteInternalRoute(props.route.id)
				: await Api.notifications.deleteRoute(code, props.route.id)
		if (res.data.success) {
			message.success("Route deleted")
			emit("deleted")
		} else {
			message.warning(res.data.message || "Failed to delete route")
		}
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "Failed to delete route")
	} finally {
		loadingDelete.value = false
	}
}
</script>
