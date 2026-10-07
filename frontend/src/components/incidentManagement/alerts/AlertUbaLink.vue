<template>
	<CardKV v-if="ubaAlertId">
		<template #key>user behavior</template>
		<template #value>
			<div class="flex flex-col gap-1">
				<a
					:href="alertPage?.href()"
					class="text-primary w-fit font-mono"
					data-testid="alert-uba-alert-link"
					@click="follow($event, alertPage)"
				>
					UBA alert
					<Icon :name="LinkIcon" :size="13" class="relative top-0.5" />
				</a>
				<a
					v-if="entityPage"
					:href="entityPage.href()"
					class="text-primary w-fit font-mono"
					data-testid="alert-uba-entity-link"
					@click="follow($event, entityPage)"
				>
					{{ entityName || entityKey }}
					<Icon :name="LinkIcon" :size="13" class="relative top-0.5" />
				</a>
			</div>
		</template>
	</CardKV>
</template>

<script setup lang="ts">
// Links an incident alert raised by SOCFortress UBA to the pages of its UBA alert and entity. UBA puts
// its own alert id and entity in the alert document, which CoPilot keeps as the asset's alert context.
// Real links: a middle-click or "open in new tab" works, a plain click navigates in the app.
import type { EntityRoute } from "@/composables/useNavigation"
import type { Alert, AlertContextDetails } from "@/types/incidentManagement/alerts"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import CardKV from "@/components/common/cards/CardKV.vue"
import Icon from "@/components/common/Icon.vue"
import { useNavigation } from "@/composables/useNavigation"

const { alert } = defineProps<{ alert: Alert }>()

const LinkIcon = "carbon:launch"

const { routeUbaAlert, routeUbaEntity } = useNavigation()
const context = ref<AlertContextDetails | null>(null)

function text(key: string) {
	const value = context.value?.[key]
	return typeof value === "string" && value ? value : undefined
}
const ubaAlertId = computed(() => text("uba_alert_id"))
const entityKey = computed(() => text("uba_entity_key"))
const entityName = computed(() => text("uba_entity_name"))

const alertPage = computed(() => (ubaAlertId.value ? routeUbaAlert(alert.customer_code, ubaAlertId.value) : null))
const entityPage = computed(() => (entityKey.value ? routeUbaEntity(alert.customer_code, entityKey.value) : null))

function follow(event: MouseEvent, page: EntityRoute | null) {
	// Leave a modified click (new tab / window) to the browser.
	if (!page || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return
	event.preventDefault()
	page.navigate()
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
