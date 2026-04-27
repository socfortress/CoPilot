<template>
	<n-spin :show="loading">
		<div class="flex flex-col gap-3">
			<div class="flex items-center justify-between">
				<n-tag :bordered="false" type="info" size="small">
					{{ events.length }} event{{ events.length === 1 ? "" : "s" }}
				</n-tag>
				<n-button size="tiny" quaternary @click="fetchTimeline">
					<template #icon><Icon name="carbon:renew" :size="14" /></template>
					Refresh
				</n-button>
			</div>

			<p class="text-secondary text-xs">
				Read-only audit log of investigation activity on this case.
			</p>

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
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { CaseEvent } from "@/types/caseTemplates"
import type { ApiError } from "@/types/common"
import { NButton, NEmpty, NSpin, NTag, NTimeline, NTimelineItem, useMessage } from "naive-ui"
import { h, onMounted, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import dayjs from "@/utils/dayjs"
import { getApiErrorMessage } from "@/utils"

const props = defineProps<{
	caseId: number
}>()

const message = useMessage()
const events = ref<CaseEvent[]>([])
const loading = ref(false)

async function fetchTimeline() {
	loading.value = true
	try {
		const res = await Api.caseTemplates.getCaseTimeline(props.caseId)
		events.value = res.data.events ?? []
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError))
	} finally {
		loading.value = false
	}
}

watch(() => props.caseId, fetchTimeline)
onMounted(fetchTimeline)

function formatDateTime(iso: string): string {
	return dayjs(iso).format("MMM D, YYYY HH:mm:ss")
}

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
			return `Notes added on task: ${p.title ?? `#${p.task_id}`}`
		default:
			return event.event_type.replace(/_/g, " ")
	}
}

function timelineType(event: CaseEvent): "default" | "success" | "info" | "warning" | "error" {
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
	if ((event.event_type === "comment_added" || event.event_type === "task_commented") && p.snippet) {
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
