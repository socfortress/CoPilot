<template>
	<div class="case-timeline flex flex-col gap-3">
		<div class="flex items-center justify-between">
			<n-tag :bordered="false" type="info" size="small">
				{{ events.length }} event{{ events.length === 1 ? "" : "s" }}
			</n-tag>
			<n-button size="tiny" quaternary @click="fetchTimeline">
				<template #icon><Icon name="carbon:renew" :size="14" /></template>
				Refresh
			</n-button>
		</div>

		<n-spin :show="loading">
			<n-timeline v-if="events.length">
				<n-timeline-item
					v-for="event in events"
					:key="event.id"
					:type="timelineType(event)"
					:time="formatDateTime(event.timestamp)"
				>
					<template #header>
						<div class="flex flex-wrap items-center gap-2">
							<Icon :name="iconFor(event)" :size="16" class="text-secondary" />
							<span class="font-medium">{{ summary(event) }}</span>
							<n-tag size="tiny" :bordered="false">{{ event.actor }}</n-tag>
						</div>
					</template>
					<div v-if="hasDetail(event)" class="text-secondary mt-1 text-sm">
						<component :is="renderDetail(event)" />
					</div>
				</n-timeline-item>
			</n-timeline>
			<n-empty v-else-if="!loading" description="No timeline events yet" class="h-32 justify-center" />
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { CaseEvent } from "@/types/incidentManagement/caseTemplates.d"
import { NButton, NEmpty, NSpin, NTag, NTimeline, NTimelineItem, useMessage } from "naive-ui"
import { h, onMounted, ref } from "vue"
import Icon from "@/components/common/Icon.vue"
import Api from "@/api"
import { formatDate } from "@/utils/format"

const props = defineProps<{
	caseId: number
}>()

const message = useMessage()
const events = ref<CaseEvent[]>([])
const loading = ref(false)

function fetchTimeline() {
	loading.value = true
	Api.incidentManagement.caseTemplates
		.getCaseTimeline(props.caseId)
		.then(res => {
			if (res.data.success) {
				events.value = res.data.events
			} else {
				message.warning(res.data.message)
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "Failed to load case timeline")
		})
		.finally(() => {
			loading.value = false
		})
}

defineExpose({ refresh: fetchTimeline })

onMounted(fetchTimeline)

function formatDateTime(iso: string): string {
	try {
		return formatDate(iso, "MMM D, YYYY HH:mm:ss") as string
	} catch {
		return iso
	}
}

// Per-event-type rendering. Falls back gracefully on unknown event types
// so a future backend addition doesn't blank-render the timeline.
function summary(event: CaseEvent): string {
	const p = (event.payload || {}) as Record<string, any>
	switch (event.event_type) {
		case "case_created":
			return p.source === "from_alert"
				? `Case created from alert #${p.alert_id}`
				: "Case created"
		case "case_status_changed":
			return p.forced
				? `Status forced from ${p.from ?? "—"} to ${p.to} (mandatory tasks bypassed)`
				: `Status changed from ${p.from ?? "—"} to ${p.to}`
		case "case_assigned":
			return p.from
				? `Reassigned from ${p.from} to ${p.to ?? "unassigned"}`
				: `Assigned to ${p.to ?? "unassigned"}`
		case "case_escalated":
			return p.escalated ? "Case escalated" : "Case de-escalated"
		case "alert_linked":
			return p.alert_ids
				? `${p.alert_ids.length} alert(s) linked to case`
				: `Alert #${p.alert_id} linked`
		case "alert_unlinked":
			return `Alert #${p.alert_id} unlinked`
		case "comment_added":
			return "Comment added"
		case "template_applied":
			return `Template applied: ${p.template_name ?? `#${p.template_id}`} (${p.tasks_added ?? 0} task${p.tasks_added === 1 ? "" : "s"})`
		case "task_added":
			return `Task added: ${p.title ?? `#${p.task_id}`}${p.mandatory ? " (mandatory)" : ""}`
		case "task_status_changed":
			return `Task ${p.title ?? `#${p.task_id}`}: ${p.from_status ?? "—"} → ${p.to_status ?? "—"}`
		case "task_commented":
			return `Evidence added on task: ${p.title ?? `#${p.task_id}`}`
		default:
			return event.event_type.replace(/_/g, " ")
	}
}

function timelineType(
	event: CaseEvent
): "default" | "success" | "info" | "warning" | "error" {
	const p = (event.payload || {}) as Record<string, any>
	switch (event.event_type) {
		case "case_created":
		case "alert_linked":
		case "template_applied":
			return "info"
		case "case_status_changed":
			return p.to === "CLOSED" ? "success" : p.to === "OPEN" ? "info" : "warning"
		case "task_status_changed":
			return p.to_status === "DONE"
				? "success"
				: p.to_status === "NOT_NECESSARY"
					? "warning"
					: "default"
		case "case_escalated":
			return p.escalated ? "warning" : "default"
		case "alert_unlinked":
			return "warning"
		case "comment_added":
		case "task_added":
		case "task_commented":
		case "case_assigned":
		default:
			return "default"
	}
}

function iconFor(event: CaseEvent): string {
	switch (event.event_type) {
		case "case_created":
			return "carbon:document-add"
		case "case_status_changed":
			return "carbon:flow-modeler"
		case "case_assigned":
			return "carbon:user-avatar-filled-alt"
		case "case_escalated":
			return "carbon:warning-alt"
		case "alert_linked":
			return "carbon:link"
		case "alert_unlinked":
			return "carbon:unlink"
		case "comment_added":
			return "carbon:chat"
		case "template_applied":
			return "carbon:flow"
		case "task_added":
			return "carbon:add-alt"
		case "task_status_changed":
			return "carbon:checkmark"
		case "task_commented":
			return "carbon:notebook"
		default:
			return "carbon:circle-dash"
	}
}

function hasDetail(event: CaseEvent): boolean {
	const p = (event.payload || {}) as Record<string, any>
	return !!(p.snippet || (event.event_type === "alert_linked" && p.alert_ids))
}

function renderDetail(event: CaseEvent) {
	const p = (event.payload || {}) as Record<string, any>
	if (event.event_type === "comment_added" && p.snippet) {
		return () =>
			h("blockquote", { class: "border-border mt-1 border-l-4 pl-3 italic" }, String(p.snippet))
	}
	if (event.event_type === "task_commented" && p.snippet) {
		return () =>
			h("blockquote", { class: "border-border mt-1 border-l-4 pl-3 italic" }, String(p.snippet))
	}
	if (event.event_type === "alert_linked" && Array.isArray(p.alert_ids)) {
		return () =>
			h(
				"span",
				{ class: "text-tertiary" },
				`Alerts: ${(p.alert_ids as number[]).map((n: number) => `#${n}`).join(", ")}`
			)
	}
	return () => h("span")
}
</script>
