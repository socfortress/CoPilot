<template>
	<div class="page">
		<div class="mb-4 flex flex-wrap items-start justify-between gap-4">
			<div class="flex max-w-3xl flex-col gap-2">
				<h1>Message templates</h1>
				<p class="text-secondary text-sm">
					Reusable message bodies that notification routes render with. Write one, attach it to as many routes
					as you like, and edit it in one place.
					<br />
					A route can still carry its own one-off template — that always wins over the shared one, so a single
					route can deviate without forking it.
				</p>
			</div>

			<n-button v-if="!showForm" size="small" type="primary" class="shrink-0" @click="openForm()">
				<template #icon>
					<Icon :name="AddIcon" :size="14" />
				</template>
				Add template
			</n-button>
		</div>

		<transition name="transition-fade" mode="out-in">
			<n-card v-if="showForm" size="small">
				<div class="flex flex-col gap-4">
					<h4>{{ formTitle }}</h4>
					<NotificationTemplateForm
						:key="formKey"
						:editing-template
						@submitted="onFormSubmitted"
						@close="closeForm()"
					/>
				</div>
			</n-card>
			<div v-else class="flex flex-col gap-4">
				<div class="flex flex-wrap items-center justify-end gap-2">
					<n-select
						v-model:value="triggerFilter"
						:options="triggerOptions"
						size="small"
						clearable
						placeholder="Any trigger"
						class="w-40!"
						:consistent-menu-width="false"
						@update:value="refreshList()"
					/>
					<n-button size="small" :disabled="loading" @click="refreshList()">
						<template #icon>
							<Icon :name="RefreshIcon" :size="14" />
						</template>
						Refresh
					</n-button>
				</div>

				<n-spin :show="loading">
					<div class="min-h-52">
						<template v-if="list.length">
							<NotificationTemplateItem
								v-for="template of list"
								:key="template.id"
								:template
								class="item-appear item-appear-bottom item-appear-005 mb-2"
								@edit="openEdit(template)"
								@duplicate="openDuplicate(template)"
								@deleted="refreshList()"
								@updated="refreshList()"
							/>
						</template>
						<n-empty
							v-else-if="!loading"
							description="No templates match. Built-in templates ship with the deployment — clear the filter to see them."
							class="h-48 justify-center"
						/>
					</div>
				</n-spin>
			</div>
		</transition>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { NotificationTemplate, NotificationTrigger } from "@/types/notifications"
import { NButton, NCard, NEmpty, NSelect, NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import { useRouter } from "vue-router"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import NotificationTemplateForm from "@/components/notifications/NotificationTemplateForm.vue"
import NotificationTemplateItem from "@/components/notifications/NotificationTemplateItem.vue"
import { getApiErrorMessage } from "@/utils"

// Deployment-level rather than nested under a customer: a template with no
// customer_code is shared with every tenant, so there's no one customer it
// belongs under. Admin-only for writes — these are shared across tenants, so a
// bad edit reaches every route using them at once.

const AddIcon = "carbon:add"
const RefreshIcon = "carbon:renew"

const message = useMessage()
const router = useRouter()

const list = ref<NotificationTemplate[]>([])
const loading = ref(false)
const showForm = ref(false)
const editingTemplate = ref<NotificationTemplate | null>(null)
const triggerFilter = ref<NotificationTrigger | null>(null)
// Bumped on every open so the form remounts with fresh state — otherwise
// editing one template then another would keep the first one's fields.
const formKey = ref(0)

const triggerOptions = [
	{ label: "Alert created", value: "alert_created" },
	{ label: "AI investigation complete", value: "investigation_complete" },
	{ label: "Alert assigned", value: "alert_assigned" },
	{ label: "Case assigned", value: "case_assigned" },
	{ label: "Case task assigned", value: "case_task_assigned" }
]

const formTitle = computed(() => {
	if (!editingTemplate.value) return "Create a template"
	// A duplicate arrives as an unsaved template with no id.
	return editingTemplate.value.id
		? `Edit ${editingTemplate.value.name}`
		: `Duplicate of ${editingTemplate.value.name}`
})

function openForm() {
	editingTemplate.value = null
	formKey.value++
	showForm.value = true
}

function openEdit(template: NotificationTemplate) {
	editingTemplate.value = template
	formKey.value++
	showForm.value = true
}

function openDuplicate(template: NotificationTemplate) {
	// A copy with no id, so the form creates rather than updates. This is how a
	// built-in becomes editable: the original stays as a reference.
	editingTemplate.value = {
		...template,
		id: 0,
		name: `${template.name} (copy)`,
		is_default: false,
		created_by: null
	}
	formKey.value++
	showForm.value = true
}

function closeForm() {
	showForm.value = false
	editingTemplate.value = null
}

function onFormSubmitted() {
	closeForm()
	refreshList()
}

function refreshList() {
	loading.value = true
	Api.notifications
		.listTemplates({ trigger: triggerFilter.value })
		.then(res => {
			if (res.data.success) {
				list.value = res.data.templates
				applyDuplicateQuery()
			} else {
				message.warning(res.data.message || "Failed to load templates")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "Failed to load templates")
		})
		.finally(() => {
			loading.value = false
		})
}

// A template's detail page hands duplication back here, since the copy is
// unsaved and the creation form lives on this page. Consumed once and dropped
// from the URL, so a refresh doesn't reopen a form the operator closed.
function applyDuplicateQuery() {
	const requested = router.currentRoute.value.query.duplicate
	if (!requested) return

	const id = Number.parseInt(Array.isArray(requested) ? (requested[0] ?? "") : requested, 10)
	const template = Number.isSafeInteger(id) ? list.value.find(item => item.id === id) : undefined

	router.replace({ query: {} })

	if (template) {
		openDuplicate(template)
	}
}

onBeforeMount(refreshList)
</script>
