<template>
	<div>
		<CardEntity hoverable :embedded class="@container">
			<template #headerMain>#{{ entity.technique_id }}</template>
			<template #headerExtra>
				<span class="text-xs whitespace-nowrap">
					test count:
					<code>{{ entity.test_count }}</code>
				</span>
			</template>
			<template #default>{{ entity.technique_name }}</template>
			<template #footerMain>
				<div class="flex flex-wrap items-center gap-3">
					<Badge v-if="entity.has_prerequisites" color="primary" type="splitted">
						<template #label>has prerequisites</template>
					</Badge>

					<Badge v-for="cat of entity.categories" :key="cat" color="primary">
						<template #iconLeft><Icon :name="iconFromOs(cat)" :size="14" /></template>
						<template #value>{{ cat }}</template>
					</Badge>
				</div>
			</template>
			<template #footerExtra>
				<div class="flex flex-wrap items-center gap-2">
					<SimulatorButton :technique-id="entity.technique_id" size="small" :os-list="entity.categories" />
					<EntityDetailsButton
						size="small"
						:url="routeAlertsAtomicRedTeamTechnique(entity.technique_id).fullUrl()"
						@view="showDetails = true"
					/>
				</div>
			</template>
		</CardEntity>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			content-class="p-0!"
			:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(600px, 90vh)', overflow: 'hidden' }"
			:title="`Technique: ${entity.technique_name}`"
			:bordered="false"
			segmented
		>
			<div class="p-6">
				<TechniqueCardContent :technique-id="entity.technique_id" />
			</div>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { MitreAtomicTest } from "@/types/mitre"
import { NModal } from "naive-ui"
import { ref } from "vue"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import EntityDetailsButton from "@/components/common/EntityDetailsButton.vue"
import Icon from "@/components/common/Icon.vue"
import { useNavigation } from "@/composables/useNavigation"
import { iconFromOs } from "@/utils"
import SimulatorButton from "../AttackSimulator/SimulatorButton.vue"
import TechniqueCardContent from "./TechniqueCardContent.vue"

const { entity } = defineProps<{ entity: MitreAtomicTest; embedded?: boolean }>()

const { routeAlertsAtomicRedTeamTechnique } = useNavigation()

const showDetails = ref(false)
</script>
