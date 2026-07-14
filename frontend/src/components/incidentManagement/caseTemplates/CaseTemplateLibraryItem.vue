<template>
	<CardEntity size="small">
		<template #headerMain>
			<div class="text-default text-base font-semibold">
				{{ entry.name }}
			</div>
		</template>
		<template #headerExtra>
			<div class="flex items-center gap-2">
				<n-button
					size="small"
					type="primary"
					secondary
					:disabled="importDisabled"
					:loading="importing"
					@click="emit('import', entry)"
				>
					<template #icon><Icon name="carbon:download" /></template>
					Import
				</n-button>

				<EntityDetailsButton
					v-if="!hideDetailsButton"
					:order="['open']"
					size="small"
					open-show-label
					:route="routeIncidentManagementCaseTemplateLibraryEntry(entry.key)"
				/>
			</div>
		</template>
		<template #default>
			<p v-if="entry.description" class="text-secondary text-sm" :class="{ 'line-clamp-3': !expanded }">
				{{ entry.description }}
			</p>
		</template>

		<template #footer>
			<div class="flex flex-wrap items-center gap-2 text-xs">
				<Badge type="splitted" size="small">
					<template #label>Source</template>
					<template #value>{{ entry.source || "—" }}</template>
				</Badge>
				<Badge type="splitted" size="small">
					<template #label>Tasks</template>
					<template #value>{{ entry.tasks.length }}</template>
				</Badge>
				<Badge v-if="mandatoryCount > 0" color="warning" type="splitted" bright size="small">
					<template #label>Mandatory</template>
					<template #value>{{ mandatoryCount }}</template>
				</Badge>
				<n-tag
					v-if="entry.match_field && entry.match_value"
					:bordered="false"
					size="small"
					type="success"
					:title="`Conditional: applies when ${entry.match_field} == ${entry.match_value}`"
				>
					{{ entry.match_field }} == {{ entry.match_value }}
				</n-tag>
				<n-tag v-for="tactic of mitreTactics" :key="tactic" size="small" :bordered="false">
					{{ tactic }}
				</n-tag>
			</div>
		</template>
	</CardEntity>
</template>

<script setup lang="ts">
import type { CaseTemplateLibraryEntry } from "@/types/incidentManagement/case-templates"
import { NButton, NTag } from "naive-ui"
import { computed } from "vue"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import EntityDetailsButton from "@/components/common/EntityDetailsButton.vue"
import Icon from "@/components/common/Icon.vue"
import { useNavigation } from "@/composables/useNavigation"

const { entry, importing, importDisabled, hideDetailsButton, expanded } = defineProps<{
	entry: CaseTemplateLibraryEntry
	importing?: boolean
	importDisabled?: boolean
	/** Hide the "open" action when the card is already the detail page's header. */
	hideDetailsButton?: boolean
	expanded?: boolean
}>()

const emit = defineEmits<{
	(e: "import", value: CaseTemplateLibraryEntry): void
}>()

const { routeIncidentManagementCaseTemplateLibraryEntry } = useNavigation()

const mandatoryCount = computed(() => entry.tasks.filter(t => t.mandatory).length)

const mitreTactics = computed<string[]>(() => {
	const raw = entry.tags?.mitre_tactics
	if (!Array.isArray(raw)) return []
	return raw.filter((t): t is string => typeof t === "string")
})
</script>
