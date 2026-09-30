<template>
	<CardKV v-if="ubaAlertId">
		<template #key>user behavior</template>
		<template #value>
			<div class="flex flex-col gap-1">
				<code class="text-primary cursor-pointer" @click="openUba({ alert: ubaAlertId })">
					UBA alert
					<Icon :name="LinkIcon" :size="13" class="relative top-0.5" />
				</code>
				<code v-if="entityKey" class="text-primary cursor-pointer" @click="openUba({ entity: entityKey })">
					{{ entityName || entityKey }}
					<Icon :name="LinkIcon" :size="13" class="relative top-0.5" />
				</code>
			</div>
		</template>
	</CardKV>
</template>

<script setup lang="ts">
// Links an incident alert raised by SOCFortress UBA back to the User Behavior page. UBA puts its
// own alert id and entity in the alert document, which CoPilot keeps as the asset's alert context.
import type { Alert, AlertContextDetails } from "@/types/incidentManagement/alerts"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import CardKV from "@/components/common/cards/CardKV.vue"
import Icon from "@/components/common/Icon.vue"
import { useNavigation } from "@/composables/useNavigation"

const { alert } = defineProps<{ alert: Alert }>()

const LinkIcon = "carbon:launch"

const { routeUba } = useNavigation()
const context = ref<AlertContextDetails | null>(null)

function text(key: string) {
	const value = context.value?.[key]
	return typeof value === "string" && value ? value : undefined
}
const ubaAlertId = computed(() => text("uba_alert_id"))
const entityKey = computed(() => text("uba_entity_key"))
const entityName = computed(() => text("uba_entity_name"))

function openUba(target: { alert?: string; entity?: string }) {
	routeUba({ customer: alert.customer_code, ...target }).navigate()
}

// Only UBA's alerts carry these fields, so other sources skip the extra request.
const contextId = computed(() =>
	alert.source?.toLowerCase() === "uba" ? alert.assets.find(a => a.alert_context_id != null)?.alert_context_id : undefined
)

watch(
	contextId,
	id => {
		context.value = null
		if (id == null) return
		Api.incidentManagement.alerts
			.getAlertContext(id)
			.then(res => {
				if (res.data.success && contextId.value === id) context.value = res.data.alert_context?.context ?? null
			})
			.catch(() => {
				// the link is a convenience: the alert page stays usable without it
			})
	},
	{ immediate: true }
)
</script>
