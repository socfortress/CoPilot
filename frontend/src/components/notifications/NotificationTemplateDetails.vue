<template>
	<n-tabs
		v-model:value="activeTab"
		type="line"
		animated
		:tabs-padding="fullWidth ? 0 : 24"
		class="grow"
		pane-wrapper-class="flex grow flex-col"
	>
		<n-tab-pane name="Overview" tab="Overview" display-directive="show:lazy" class="flex grow flex-col">
			<div class="flex flex-col gap-4" :class="fullWidth ? 'p-0' : 'p-5 pt-3'">
				<div class="grid grid-cols-6 gap-4">
					<CardKV class="col-span-6 md:col-span-3">
						<template #key>name</template>
						<template #value>{{ entity.name }}</template>
					</CardKV>
					<CardKV class="col-span-3 md:col-span-3">
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
				</div>

				<div class="border-default bg-secondary flex flex-wrap items-center gap-3 rounded-lg border p-3">
					<Badge type="splitted">
						<template #label># ID</template>
						<template #value>{{ entity.id }}</template>
					</Badge>

					<Badge type="splitted" color="primary">
						<template #label>format</template>
						<template #value>{{ entity.format }}</template>
					</Badge>

					<Badge type="splitted">
						<template #label>trigger</template>
						<template #value>{{ triggerLabel }}</template>
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
							<span v-else>all customers</span>
						</template>
					</Badge>

					<Badge v-if="entity.is_default" type="splitted" color="warning">
						<template #label>built-in</template>
						<template #value>read-only</template>
					</Badge>

					<Badge v-if="entity.updated_at" type="splitted">
						<template #iconLeft>
							<Icon :name="TimeIcon" />
						</template>
						<template #label>updated</template>
						<template #value>{{ formatDate(entity.updated_at, dFormats.datetimesec) }}</template>
					</Badge>
				</div>

				<CardKV size="lg">
					<template #key>description</template>
					<template #value>{{ entity.description || "—" }}</template>
				</CardKV>

				<!--
					Kept out of the source tab: email needs a subject and a Teams card
					needs a title, so whether one is set is a property of the template
					worth seeing without reading its body.
				-->
				<CardKV size="lg">
					<template #key>subject</template>
					<template #value>{{ entity.subject_template || "not set" }}</template>
				</CardKV>
			</div>
		</n-tab-pane>

		<n-tab-pane name="Source" tab="Source" display-directive="show:lazy">
			<div class="flex flex-col gap-4" :class="fullWidth ? 'p-0' : 'p-5 pt-3'">
				<div v-if="entity.subject_template" class="flex flex-col gap-1">
					<div class="text-secondary px-1 text-xs uppercase">Subject template</div>
					<CodeSource :code="entity.subject_template" lang="text" />
				</div>

				<div class="flex flex-col gap-1">
					<div class="text-secondary px-1 text-xs uppercase">Body template</div>
					<CodeSource :code="entity.body_template" :lang="sourceLang" />
				</div>
			</div>
		</n-tab-pane>

		<!--
			Rendered against a sample event by the same endpoint the editor uses, so
			what this shows can't drift from what a real dispatch would send.
		-->
		<n-tab-pane name="Preview" tab="Preview" display-directive="show:lazy">
			<n-spin :show="previewing">
				<div class="flex min-h-40 flex-col gap-4" :class="fullWidth ? 'p-0' : 'p-5 pt-3'">
					<div
						class="border-default bg-secondary flex flex-wrap items-center justify-between gap-3 rounded-lg border p-3"
					>
						<div class="text-secondary flex items-center gap-2 text-xs">
							<Icon :name="InfoIcon" :size="14" class="shrink-0" />
							<span>Rendered against a sample event, not this customer's real data.</span>
						</div>
						<n-button size="tiny" secondary :loading="previewing" @click="loadPreview()">
							<template #icon>
								<Icon :name="RefreshIcon" :size="14" />
							</template>
							Refresh
						</n-button>
					</div>

					<n-alert v-if="preview?.error" type="warning" :bordered="false" title="Render failed">
						{{ preview.error }}
					</n-alert>

					<template v-else-if="preview">
						<CardKV v-if="preview.subject">
							<template #key>subject</template>
							<template #value>{{ preview.subject }}</template>
						</CardKV>

						<div class="flex flex-col gap-1">
							<div class="text-secondary px-1 text-xs uppercase">Body</div>

							<!--
								A sandboxed iframe, not v-html: the body is operator-authored
								and renders in an admin's browser, so v-html would let a
								template author run script in the viewer's session.
							-->
							<div
								v-if="entity.format === 'html'"
								class="border-default overflow-hidden rounded-lg border bg-white"
							>
								<iframe :srcdoc="preview.body" sandbox="" title="HTML preview" class="h-96 w-full" />
							</div>

							<!--
								Keyed on the body: the highlighter runs once per element, so
								a re-render after Refresh would otherwise keep the old output.
							-->
							<CodeSource v-else :key="preview.body" :code="preview.body" :lang="sourceLang" />
						</div>
					</template>

					<n-empty
						v-else-if="!previewing"
						description="No preview yet — render one to see what this template sends."
						class="h-32 justify-center"
					/>
				</div>
			</n-spin>
		</n-tab-pane>
	</n-tabs>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { NotificationTemplate, NotificationTrigger, TemplatePreviewResult } from "@/types/notifications"
import { NAlert, NButton, NEmpty, NSpin, NTabPane, NTabs } from "naive-ui"
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

const props = defineProps<{
	entity: NotificationTemplate
	fullWidth?: boolean
}>()

const { entity, fullWidth } = toRefs(props)

const LinkIcon = "carbon:launch"
const TimeIcon = "carbon:time"
const RefreshIcon = "carbon:renew"
const InfoIcon = "carbon:information"

const TRIGGER_LABELS: Record<NotificationTrigger, string> = {
	alert_created: "Alert created",
	investigation_complete: "AI investigation complete",
	ai_report_reviewed: "AI report reviewed",
	alert_assigned: "Alert assigned",
	case_assigned: "Case assigned",
	case_task_assigned: "Case task assigned",
	temp_password_issued: "Temporary password email"
}

const dFormats = useSettingsStore().dateFormat
const { routeCustomer } = useNavigation()

const activeTab = ref("Overview")
const previewing = ref(false)
const preview = ref<TemplatePreviewResult | null>(null)

const triggerLabel = computed(() =>
	entity.value.trigger ? (TRIGGER_LABELS[entity.value.trigger] ?? entity.value.trigger) : "any"
)

// Only the languages bundled in utils/highlighter are highlighted; anything
// else falls back to plain text rather than failing to render.
const sourceLang = computed(() => {
	if (entity.value.format === "html") return "html"
	if (entity.value.format === "json") return "json"
	if (entity.value.format === "markdown") return "markdown"
	return "text"
})

// Fetched on first visit rather than on mount — the preview is a round trip per
// template, and most opens never leave the Overview tab.
watch(activeTab, tab => {
	if (tab === "Preview" && !preview.value && !previewing.value) {
		loadPreview()
	}
})

// A render failure comes back in `error` rather than as a non-2xx, so a broken
// built-in still shows its source instead of blanking the tab.
async function loadPreview() {
	previewing.value = true

	try {
		const res = await Api.notifications.previewTemplate({
			body_template: entity.value.body_template,
			subject_template: entity.value.subject_template,
			format: entity.value.format,
			trigger: entity.value.trigger ?? undefined,
			customer_code: entity.value.customer_code
		})
		preview.value = { body: res.data.body, subject: res.data.subject, error: res.data.error }
	} catch (err) {
		preview.value = {
			body: "",
			subject: null,
			error: getApiErrorMessage(err as ApiError) || "Could not render a preview."
		}
	} finally {
		previewing.value = false
	}
}
</script>
