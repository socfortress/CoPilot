<template>
	<n-spin :show="loading">
		<div class="flex flex-col gap-3">
			<div class="flex items-center justify-between">
				<Chip :value="events.length" :label="$t('cases.caseTimeline.events')" :bordered="false" />

				<n-button size="small" secondary @click="fetchTimeline">
					<template #icon><Icon name="carbon:renew" /></template>
					{{ $t("common.actions.refresh") }}
				</n-button>
			</div>

			<p class="text-secondary text-xs">{{ $t("cases.caseTimeline.intro") }}</p>

			<n-timeline v-if="events.length">
				<n-timeline-item
					v-for="event in events"
					:key="event.id"
					:type="timelineType(event)"
					:time="formatDate(event.timestamp, dFormats.datetimesec).toString()"
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
			<n-empty v-else-if="!loading" :description="$t('cases.caseTimeline.empty')" class="h-32 justify-center" />
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { CaseEvent } from "@/types/caseTemplates"
import type { ApiError } from "@/types/common"
import { NButton, NEmpty, NSpin, NTag, NTimeline, NTimelineItem, useMessage } from "naive-ui"
import { h, ref, watch } from "vue"
import { useI18n } from "vue-i18n"
import Api from "@/api"
import Chip from "@/components/common/Chip.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"
import { workflowStatusLabel } from "@/utils/workflowStatus"

const props = defineProps<{
	caseId: number
}>()

const dFormats = useSettingsStore().dateFormat

const message = useMessage()
const { t } = useI18n()
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

function statusText(status: string | null | undefined): string {
	return status ? workflowStatusLabel(status) : "—"
}

function summary(event: CaseEvent): string {
	const p = (event.payload || {}) as Record<string, any>
	switch (event.event_type) {
		case "case_created":
			return p.source === "from_alert"
				? t("cases.caseTimeline.caseCreatedFromAlert", { id: p.alert_id })
				: t("cases.caseTimeline.caseCreated")
		case "case_status_changed":
			return t(p.forced ? "cases.caseTimeline.statusForced" : "cases.caseTimeline.statusChanged", {
				from: statusText(p.from),
				to: statusText(p.to)
			})
		case "case_assigned": {
			const to = p.to ?? t("cases.caseTimeline.unassigned")
			return p.from
				? t("cases.caseTimeline.reassigned", { from: p.from, to })
				: t("cases.caseTimeline.assigned", { to })
		}
		case "case_escalated":
			return t(p.escalated ? "cases.caseTimeline.escalated" : "cases.caseTimeline.deescalated")
		case "alert_linked":
			return p.alert_ids
				? t("cases.caseTimeline.alertsLinked", { count: p.alert_ids.length })
				: t("cases.caseTimeline.alertLinked", { id: p.alert_id })
		case "alert_unlinked":
			return t("cases.caseTimeline.alertUnlinked", { id: p.alert_id })
		case "comment_added":
			return t("cases.caseTimeline.commentAdded")
		case "template_applied":
			return t("cases.caseTimeline.templateApplied", {
				name: p.template_name ?? `#${p.template_id}`,
				count: p.tasks_added ?? 0
			}, p.tasks_added ?? 0)
		case "task_added":
			return t(p.mandatory ? "cases.caseTimeline.taskAddedMandatory" : "cases.caseTimeline.taskAdded", {
				title: p.title ?? `#${p.task_id}`
			})
		case "task_status_changed":
			return t("cases.caseTimeline.taskStatusChanged", {
				title: p.title ?? `#${p.task_id}`,
				from: p.from_status ?? "—",
				to: p.to_status ?? "—"
			})
		case "task_commented":
			return t("cases.caseTimeline.taskCommented", { title: p.title ?? `#${p.task_id}` })
		default:
			return String(event.event_type).replace(/_/g, " ")
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
			// Waiting on the customer reads as the in-between states do: the item is not done.
			return p.to === "CLOSED" ? "success" : p.to === "OPEN" ? "info" : "warning"
		case "task_status_changed":
			return p.to_status === "DONE" ? "success" : p.to_status === "NOT_NECESSARY" ? "warning" : "default"
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
		return () => h("blockquote", { class: "border-border mt-1 border-l-4 pl-3 italic" }, String(p.snippet))
	}
	if (event.event_type === "alert_linked" && Array.isArray(p.alert_ids)) {
		return () =>
			h(
				"span",
				{ class: "text-tertiary" },
				t("cases.caseTimeline.alertsDetail", {
					list: (p.alert_ids as number[]).map((n: number) => `#${n}`).join(", ")
				})
			)
	}
	return () => h("span")
}

watch(() => props.caseId, fetchTimeline, { immediate: true })
</script>
