<template>
	<div>
		<CardEntity hoverable clickable :embedded class="@container" @click.stop="showDetails = true">
			<template #headerMain>#{{ entity.technique_id }}</template>
			<template #headerExtra>
				test count:
				<code>{{ entity.test_count }}</code>
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
				<SimulatorButton :technique-id="entity.technique_id" size="small" :os-list="entity.categories" />
			</template>
		</CardEntity>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(600px, 90vh)', overflow: 'hidden' }"
			:title="`Technique: ${entity.technique_name}`"
			:bordered="false"
			segmented
		>
			<TechniqueCardContent :technique-id="entity.technique_id" />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { MitreAtomicTest } from "@/types/mitre.d"
import { NModal } from "naive-ui"
import { ref } from "vue"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { iconFromOs } from "@/utils"
import SimulatorButton from "../AttackSimulator/SimulatorButton.vue"
import TechniqueCardContent from "./TechniqueCardContent.vue"

const { entity } = defineProps<{ entity: MitreAtomicTest; embedded?: boolean }>()

const showDetails = ref(false)
</script>
