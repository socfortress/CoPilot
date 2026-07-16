<template>
	<div class="page flex flex-col gap-4">
		<DetailPageHeader :title="entry?.name" :back-route="routeIncidentManagementCaseTemplates()">
			<template v-if="entry" #meta>
				<span class="text-secondary font-mono text-sm">{{ entry.key }}</span>
			</template>
		</DetailPageHeader>

		<n-spin v-if="entryKey" :show="loading" class="min-h-40" content-class="flex flex-col gap-4">
			<template v-if="entry">
				<CaseTemplateLibraryItem
					:entry
					expanded
					hide-details-button
					:importing="showImport"
					@import="openImport()"
				/>

				<div class="flex flex-col gap-2">
					<h3>Tasks</h3>
					<template v-if="orderedTasks.length">
						<CardEntity v-for="task of orderedTasks" :key="`${task.order_index}-${task.title}`" embedded>
							<template #headerMain>#{{ task.order_index }}</template>
							<template #headerExtra>
								<Badge v-if="task.mandatory" type="splitted" size="small" color="warning">
									<template #value>mandatory</template>
								</Badge>
							</template>
							<template #default>{{ task.title }}</template>
							<template v-if="task.description || task.guidelines" #mainExtra>
								<div class="flex flex-col gap-2">
									<p v-if="task.description" class="whitespace-pre-wrap">{{ task.description }}</p>
									<p v-if="task.guidelines" class="text-secondary text-sm whitespace-pre-wrap">
										{{ task.guidelines }}
									</p>
								</div>
							</template>
						</CardEntity>
					</template>
					<n-empty v-else description="No tasks defined" class="h-24 justify-center" />
				</div>

				<CardKV v-if="entry.file_path">
					<template #key>source file</template>
					<template #value>
						<code>{{ entry.file_path }}</code>
					</template>
				</CardKV>
			</template>

			<n-empty v-else-if="!loading" description="Library entry not found" class="h-32 justify-center" />
		</n-spin>
		<n-empty v-else description="Invalid library entry key" class="h-48 justify-center" />

		<CaseTemplateLibraryImportModal v-model:show="showImport" :entry @imported="onImported()" />
	</div>
</template>

<script setup lang="ts">
import type { CaseTemplateLibraryEntry } from "@/types/incidentManagement/case-templates"
import { NEmpty, NSpin } from "naive-ui"
import { computed, ref } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import CardKV from "@/components/common/cards/CardKV.vue"
import DetailPageHeader from "@/components/common/DetailPageHeader.vue"
import CaseTemplateLibraryImportModal from "@/components/incidentManagement/caseTemplates/CaseTemplateLibraryImportModal.vue"
import CaseTemplateLibraryItem from "@/components/incidentManagement/caseTemplates/CaseTemplateLibraryItem.vue"
import { useEntityDetails } from "@/composables/useEntityDetails"
import { useNavigation, useRouteParam } from "@/composables/useNavigation"

const { routeIncidentManagementCaseTemplates } = useNavigation()

const showImport = ref(false)

const entryKey = useRouteParam("key")

const { loading, entity: entry } = useEntityDetails<CaseTemplateLibraryEntry, string>({
	entity: () => null,
	id: () => entryKey.value,
	// the endpoint takes no abort signal, so the request itself is not cancellable
	fetch: key =>
		Api.incidentManagement.caseTemplates.getLibraryEntry(key).then(res => ({
			entity: res.data.success ? (res.data.entry ?? null) : null,
			message: res.data.message
		})),
	notFoundMessage: "Library entry not found",
	errorMessage: "Failed to load library entry"
})

const orderedTasks = computed(() => [...(entry.value?.tasks ?? [])].sort((a, b) => a.order_index - b.order_index))

function openImport() {
	showImport.value = true
}

function onImported() {
	showImport.value = false
	// the entry is now a real template — land the user on the templates list
	routeIncidentManagementCaseTemplates().replace()
}
</script>
