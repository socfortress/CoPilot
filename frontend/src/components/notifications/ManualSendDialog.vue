<template>
	<n-modal
		v-model:show="visible"
		preset="card"
		:title="`Send ${entityLabel} to a channel`"
		class="max-w-2xl"
		:bordered="false"
		segmented
	>
		<n-spin :show="loadingRoutes">
			<div class="flex flex-col gap-4">
				<n-alert type="info" :bordered="false">
					This sends a <strong>real notification</strong> now — it consumes provider quota and is recorded
					in the dispatch log, exactly like an automatic one.
				</n-alert>

				<n-form-item label="Send to" :show-feedback="false">
					<n-select
						v-model:value="routeId"
						:options="routeOptions"
						:loading="loadingRoutes"
						placeholder="Pick a configured route"
						@update:value="onRouteChange"
					/>
				</n-form-item>

				<!--
					Customer routes are shown-but-disabled for non-admins rather than
					hidden: the capability stays discoverable, and someone who needs it
					knows to ask. The server enforces this regardless.
				-->
				<div v-if="!isAdmin" class="text-secondary text-xs">
					Sending to a customer-facing route requires admin. Internal routes are available to you.
				</div>

				<div v-if="!loadingRoutes && !routeOptions.length" class="text-secondary text-sm">
					No routes are configured yet. Add one under
					<strong>Customers → Notifications</strong>
					or
					<strong>Internal Notifications</strong>.
				</div>

				<n-form-item v-if="selectedRoute" :show-feedback="false">
					<n-checkbox v-model:checked="includeAiReport">Include the AI investigation report</n-checkbox>
				</n-form-item>

				<div v-if="preview !== null" class="flex flex-col gap-1">
					<div class="text-secondary text-xs uppercase">Preview — exactly what will be sent</div>
					<!-- Only present when the route's template sets one. -->
					<div v-if="previewSubject" class="mb-1 text-xs">
						<span class="text-secondary">Subject:</span>
						<span class="font-mono">{{ previewSubject }}</span>
					</div>
					<n-input
						:value="preview"
						type="textarea"
						readonly
						:autosize="{ minRows: 4, maxRows: 14 }"
						class="font-mono text-xs!"
					/>
				</div>

				<n-alert v-if="previewError" type="warning" :bordered="false">{{ previewError }}</n-alert>
			</div>
		</n-spin>

		<template #footer>
			<div class="flex items-center justify-end gap-2">
				<n-button @click="visible = false">Cancel</n-button>
				<n-button secondary :disabled="!routeId" :loading="previewing" @click="loadPreview">
					Preview
				</n-button>
				<n-button type="primary" :disabled="!routeId" :loading="sending" @click="send">
					<template #icon>
						<Icon :name="SendIcon" :size="14" />
					</template>
					Send now
				</n-button>
			</div>
		</template>
	</n-modal>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { NotificationRoute } from "@/types/notifications"
import { NAlert, NButton, NCheckbox, NFormItem, NInput, NModal, NSelect, NSpin, useMessage } from "naive-ui"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useAuthStore } from "@/stores/auth"
import { getApiErrorMessage } from "@/utils"

// One dialog for both alerts and cases — they differ only in what is being sent,
// so a second component would be the same code with one string changed.
//
// Everything enforced here is ALSO enforced server-side: the customer/internal
// split, the admin requirement, the tenant match, and the AI opt-out. This is
// affordance, not access control — see app/notifications/services/manual_send.py.

const props = defineProps<{
	entityType: "alert" | "case"
	entityId: number
	// Used to narrow the route list. An item's own customer plus internal routes
	// are the only valid targets; the server re-checks the one that's submitted.
	customerCode?: string | null
}>()

const visible = defineModel<boolean>("show", { default: false })

const SendIcon = "carbon:send-alt"

const message = useMessage()
const authStore = useAuthStore()

const routes = ref<NotificationRoute[]>([])
const routeId = ref<number | null>(null)
const includeAiReport = ref(false)
const preview = ref<string | null>(null)
const previewSubject = ref<string | null>(null)
const previewError = ref<string | null>(null)
const loadingRoutes = ref(false)
const previewing = ref(false)
const sending = ref(false)

const isAdmin = computed(() => authStore.isAdmin)
const entityLabel = computed(() => (props.entityType === "alert" ? "alert" : "case"))
const selectedRoute = computed(() => routes.value.find(r => r.id === routeId.value) ?? null)

const routeOptions = computed(() =>
	routes.value.map(route => {
		const isCustomerRoute = route.scope === "customer"
		// Disabled rather than absent, with the reason in the label — a missing
		// option looks like a bug, a disabled one explains itself.
		const blocked = isCustomerRoute && !isAdmin.value
		return {
			label: `${route.name} · ${route.channel}${isCustomerRoute ? "" : " (internal)"}${blocked ? " — admin only" : ""}`,
			value: route.id,
			disabled: blocked || !route.enabled
		}
	})
)

async function loadRoutes() {
	loadingRoutes.value = true
	routes.value = []
	try {
		// An item can only target its own customer's routes plus internal ones.
		// Both lists are fetched because they live at different endpoints —
		// internal routes belong to no tenant and sit outside /customers/.
		const requests: Promise<NotificationRoute[]>[] = []

		if (props.customerCode) {
			requests.push(
				Api.notifications
					.listRoutes(props.customerCode)
					.then(res => (res.data.success ? res.data.routes : []))
					.catch(() => [])
			)
		}
		requests.push(
			Api.notifications
				.getInternalRoutes()
				.then(res => (res.data.success ? res.data.routes : []))
				// Non-admins are refused this endpoint; an empty list is the right
				// outcome, not an error worth showing.
				.catch(() => [])
		)

		routes.value = (await Promise.all(requests)).flat()
	} finally {
		loadingRoutes.value = false
	}
}

function onRouteChange() {
	// A preview belongs to one route; keeping a stale one would show the operator
	// something other than what they're about to send.
	preview.value = null
	previewSubject.value = null
	previewError.value = null
}

function payload() {
	return {
		entity_type: props.entityType,
		entity_id: props.entityId,
		route_id: routeId.value as number,
		include_ai_report: includeAiReport.value
	}
}

async function loadPreview() {
	previewing.value = true
	previewError.value = null
	try {
		const res = await Api.notifications.manualSendPreview(payload())
		preview.value = res.data.body
		previewSubject.value = res.data.subject
	} catch (err) {
		preview.value = null
		previewSubject.value = null
		previewError.value = getApiErrorMessage(err as ApiError) || "Could not render a preview."
	} finally {
		previewing.value = false
	}
}

async function send() {
	sending.value = true
	try {
		const res = await Api.notifications.manualSend(payload())
		if (res.data.status === "sent") {
			message.success(`Sent via ${res.data.channel} in ${res.data.latency_ms ?? "?"}ms`)
			visible.value = false
		} else {
			// A refused or failed delivery is information, not an exception — the
			// endpoint reports the outcome and the reason belongs on screen.
			message.warning(res.data.error_message || `Send ${res.data.status}`)
		}
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "Failed to send.")
	} finally {
		sending.value = false
	}
}

watch(visible, isOpen => {
	if (isOpen) {
		routeId.value = null
		includeAiReport.value = false
		preview.value = null
		previewSubject.value = null
		previewError.value = null
		loadRoutes()
	}
})
</script>
