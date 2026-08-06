<template>
	<n-tabs
		type="line"
		animated
		:tabs-padding="fullWidth ? 0 : 24"
		class="grow"
		pane-wrapper-class="flex min-h-100 grow flex-col"
	>
		<n-tab-pane name="Overview" tab="Overview" display-directive="show:lazy" class="flex grow flex-col">
			<n-spin :show="updatingStatus" class="flex grow flex-col" content-class="flex grow flex-col">
				<div class="flex flex-col gap-4" :class="fullWidth ? 'p-0' : 'p-5 pt-3'">
					<div class="grid grid-cols-6 gap-4">
						<CardKV class="col-span-6 md:col-span-2">
							<template #key>name</template>
							<template #value>{{ entity.name }}</template>
						</CardKV>
						<CardKV class="col-span-3 md:col-span-2">
							<template #key>creator</template>
							<template #value>
								<div class="flex flex-col gap-2 py-1">
									<div>
										<span class="text-secondary">by:</span>
										{{ entity.created_by ?? "—" }}
									</div>
									<div>
										<span class="text-secondary">at:</span>
										{{ formatDate(entity.created_at, dFormats.datetimesec) }}
									</div>
								</div>
							</template>
						</CardKV>
						<CardKV class="col-span-3 md:col-span-2">
							<template #key>status</template>
							<template #value>
								<div class="flex h-full w-full items-center justify-center font-sans">
									<n-button
										size="small"
										secondary
										:type="entity.enabled ? 'warning' : 'success'"
										:loading="updatingStatus"
										@click="toggleEnabled()"
									>
										<template #icon>
											<Icon :name="entity.enabled ? PauseIcon : PlayIcon" />
										</template>
										{{ entity.enabled ? "Disable" : "Enable" }}
									</n-button>
								</div>
							</template>
						</CardKV>
					</div>

					<div class="border-default bg-secondary flex flex-wrap items-center gap-3 rounded-lg border p-3">
						<Badge type="splitted">
							<template #label># ID</template>
							<template #value>{{ entity.id }}</template>
						</Badge>

						<Badge type="splitted" color="primary">
							<template #iconLeft>
								<Icon :name="channelIcon" />
							</template>
							<template #label>channel</template>
							<template #value>{{ channelLabel }}</template>
						</Badge>

						<Badge type="splitted">
							<template #label>trigger</template>
							<template #value>{{ triggerLabel }}</template>
						</Badge>

						<Badge type="splitted" :color="severityColor">
							<template #label>min severity</template>
							<template #value>{{ entity.min_severity }}</template>
						</Badge>

						<Badge type="splitted">
							<template #label>scope</template>
							<template #value>
								<code
									v-if="entity.customer_code"
									class="text-primary cursor-pointer leading-none"
									@click.stop="routeCustomer({ code: entity.customer_code }).navigate()"
								>
									#{{ entity.customer_code }}
									<Icon :name="LinkIcon" :size="14" class="relative top-0.5" />
								</code>
								<span v-else>internal</span>
							</template>
						</Badge>

						<Badge type="splitted">
							<template #label>dispatch</template>
							<template #value>{{ entity.dispatch_count }}</template>
						</Badge>

						<Badge type="splitted">
							<template #iconLeft>
								<Icon :name="TimeIcon" />
							</template>
							<template #label>fired</template>
							<template #value>
								{{
									entity.last_dispatched_at
										? formatDate(entity.last_dispatched_at, dFormats.datetimesec)
										: "never"
								}}
							</template>
						</Badge>

						<Badge v-if="entity.updated_at" type="splitted">
							<template #label>updated</template>
							<template #value>{{ formatDate(entity.updated_at, dFormats.datetimesec) }}</template>
						</Badge>
					</div>

					<div class="grid grid-cols-6 gap-4">
						<CardKV class="col-span-6 md:col-span-3">
							<template #key>{{ destination.label }}</template>
							<template #value>
								<div v-if="destination.values.length" class="flex flex-wrap gap-1 py-1">
									<code v-for="value in destination.values" :key="value" class="break-all">
										{{ value }}
									</code>
								</div>
								<span v-else class="italic">{{ destination.note }}</span>
							</template>
						</CardKV>

						<!--
							'assignee' resolves the address from the event at dispatch
							time, which is why the destination above can legitimately
							be empty — worth stating next to it rather than in a tooltip.
						-->
						<CardKV class="col-span-3 md:col-span-2">
							<template #key>recipient mode</template>
							<template #value>{{ entity.recipient_mode }}</template>
						</CardKV>

						<CardKV class="col-span-3 md:col-span-1">
							<template #key>self-assign</template>
							<template #value>{{ entity.notify_on_self_assign ? "notifies" : "silent" }}</template>
						</CardKV>
					</div>
				</div>
			</n-spin>
		</n-tab-pane>

		<n-tab-pane name="Channel config" tab="Channel config" display-directive="show:lazy">
			<div class="flex flex-col gap-4" :class="fullWidth ? 'p-0' : 'p-5 pt-3'">
				<!--
					The shape is owned by the backend provider's config schema, so it is
					rendered as-is rather than field-by-field: a new channel must not
					need a frontend change to be inspectable.
				-->
				<CodeSource v-if="hasConfig" :code="entity.config" lang="json" />
				<n-empty v-else description="This channel needs no configuration." class="h-32 justify-center" />

				<CardKV v-if="entity.shuffle_integration_id != null">
					<template #key>shuffle integration</template>
					<template #value>#{{ entity.shuffle_integration_id }}</template>
				</CardKV>
			</div>
		</n-tab-pane>

		<n-tab-pane name="Message" tab="Message" display-directive="show:lazy">
			<n-spin :show="loadingTemplate">
				<div class="flex min-h-40 flex-col gap-4" :class="fullWidth ? 'p-0' : 'p-5 pt-3'">
					<!--
						Precedence at send time is format_template -> template_id -> the
						channel default, so both are shown when both are set: the inline
						one wins and the named one would otherwise look active.
					-->
					<div v-if="entity.format_template" class="flex flex-col gap-1">
						<div class="text-secondary text-xs uppercase">
							Inline template — overrides the named one below
						</div>
						<CodeSource :code="entity.format_template" lang="text" />
					</div>

					<CardKV v-if="entity.template_id != null">
						<template #key>named template</template>
						<template #value>
							<code
								class="text-primary cursor-pointer leading-none"
								@click.stop="routeMessageTemplate(entity.template_id ?? undefined).navigate()"
							>
								{{ namedTemplate?.name ?? `#${entity.template_id}` }}
								<Icon :name="LinkIcon" :size="14" class="relative top-0.5" />
							</code>
						</template>
					</CardKV>

					<n-empty
						v-if="!entity.format_template && entity.template_id == null"
						description="No template attached — this route sends the channel's default message."
						class="h-32 justify-center"
					/>
				</div>
			</n-spin>
		</n-tab-pane>
	</n-tabs>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type {
	NotificationRoute,
	NotificationScope,
	NotificationTemplate,
	NotificationTrigger
} from "@/types/notifications"
import { NButton, NEmpty, NSpin, NTabPane, NTabs, useMessage } from "naive-ui"
import { computed, ref, toRefs, watch } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardKV from "@/components/common/cards/CardKV.vue"
import CodeSource from "@/components/common/CodeSource.vue"
import Icon from "@/components/common/Icon.vue"
import { useNavigation } from "@/composables/useNavigation"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"
import { describeRouteChannel, describeRouteDestination } from "./destination"

const props = defineProps<{
	entity: NotificationRoute
	// Passed down rather than read off the route: `customer_code` is nullable
	// (internal routes belong to no tenant) while the customer-scoped API paths
	// need a concrete code.
	customerCode?: string
	scope?: NotificationScope
	fullWidth?: boolean
}>()

const emit = defineEmits<{
	(e: "toggled"): void
}>()

const { entity, fullWidth } = toRefs(props)

const LinkIcon = "carbon:launch"
const TimeIcon = "carbon:time"
const PauseIcon = "carbon:pause"
const PlayIcon = "carbon:play"

const TRIGGER_LABELS: Record<NotificationTrigger, string> = {
	alert_created: "Alert created",
	investigation_complete: "AI investigation complete",
	ai_report_reviewed: "AI report reviewed",
	alert_assigned: "Alert assigned",
	case_assigned: "Case assigned",
	case_task_assigned: "Case task assigned",
	// Never reachable on a route — the backend rejects it as a route trigger —
	// but the map is exhaustive over NotificationTrigger, so it needs a label.
	temp_password_issued: "Temporary password email"
}

const message = useMessage()
const dFormats = useSettingsStore().dateFormat
const { routeCustomer, routeMessageTemplate } = useNavigation()

const updatingStatus = ref(false)
const loadingTemplate = ref(false)
const namedTemplate = ref<NotificationTemplate | null>(null)

const isInternalScope = computed(() => props.scope === "internal" || entity.value.customer_code === null)
const destination = computed(() => describeRouteDestination(entity.value))
const hasConfig = computed(() => Object.keys(entity.value.config ?? {}).length > 0)

const triggerLabel = computed(() => TRIGGER_LABELS[entity.value.trigger] ?? entity.value.trigger)

// Shared with the list row so the two can't disagree about what a route is.
const channelIcon = computed(() => describeRouteChannel(entity.value).icon)
const channelLabel = computed(() => describeRouteChannel(entity.value).label)

const severityColor = computed<"danger" | "warning" | "success">(() => {
	if (entity.value.min_severity === "Critical" || entity.value.min_severity === "High") return "danger"
	if (entity.value.min_severity === "Medium") return "warning"
	return "success"
})

// Only the name is needed, and only when a named template is attached — the
// route row stores the id alone, so this is the one lookup that makes the
// attachment readable instead of a bare number.
watch(
	() => entity.value.template_id,
	templateId => {
		namedTemplate.value = null
		if (templateId == null) return

		loadingTemplate.value = true
		Api.notifications
			.getTemplate(templateId)
			.then(res => {
				if (res.data.success) {
					namedTemplate.value = res.data.template
				}
			})
			.catch(() => {
				// A deleted template leaves the id showing, which is the honest
				// fallback — the route really does point at nothing.
			})
			.finally(() => {
				loadingTemplate.value = false
			})
	},
	{ immediate: true }
)

async function toggleEnabled() {
	updatingStatus.value = true

	try {
		const payload = { enabled: !entity.value.enabled }
		const code = props.customerCode ?? entity.value.customer_code
		const res =
			isInternalScope.value || !code
				? await Api.notifications.updateInternalRoute(entity.value.id, payload)
				: await Api.notifications.updateRoute(code, entity.value.id, payload)

		if (res.data.success) {
			entity.value.enabled = res.data.route.enabled
			message.success(`Route ${res.data.route.enabled ? "enabled" : "disabled"}`)
			emit("toggled")
		} else {
			message.warning(res.data.message || "Failed to toggle route")
		}
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "Failed to toggle route")
	} finally {
		updatingStatus.value = false
	}
}
</script>
