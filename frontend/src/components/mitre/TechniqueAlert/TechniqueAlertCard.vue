<template>
	<div>
		<CardEntity embedded clickable hoverable size="small" @click="showDetails = true">
			<template #header>
				<div class="flex items-start justify-between gap-4">
					<div>
						{{ entity.technique_id }} •
						<span class="text-default">{{ entity.technique_name }}</span>
					</div>

					<div class="flex items-center gap-2 whitespace-nowrap">
						<n-tooltip>
							<template #trigger>
								<Icon name="carbon:time" :size="16" />
							</template>
							<div class="flex flex-wrap gap-2 text-xs">
								<span class="text-secondary">last seen:</span>
								<span>{{ formatDate(entity.last_seen, dFormats.datetimesec) }}</span>
							</div>
						</n-tooltip>
						<code>
							{{ entity.count }}
						</code>
					</div>
				</div>
			</template>
		</CardEntity>
		<n-modal
			v-model:show="showDetails"
			display-directive="show"
			preset="card"
			content-class="p-0!"
			:style="{ maxWidth: 'min(900px, 90vw)', minHeight: 'min(600px, 90vh)', overflow: 'hidden' }"
			:title="`${entity.technique_id} • ${entity.technique_name}`"
			:bordered="false"
			segmented
		>
			<TechniqueAlertOverview :external-id="entity.technique_id" />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { MitreTechnique } from "@/types/mitre.d"
import { NModal, NTooltip } from "naive-ui"
import { ref } from "vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"
import TechniqueAlertOverview from "./TechniqueAlertOverview.vue"

const { entity } = defineProps<{
	entity: MitreTechnique
}>()

const dFormats = useSettingsStore().dateFormat
const showDetails = ref(false)
</script>
