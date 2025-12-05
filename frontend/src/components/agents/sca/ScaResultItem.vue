<template>
	<div>
		<CardEntity :embedded hoverable>
			<template #headerMain>#{{ data.id }}</template>
			<template #headerExtra>
				<n-button size="small" @click.stop="showDetails = true">
					<template #icon>
						<Icon :name="DetailsIcon" />
					</template>
					Details
				</n-button>
			</template>
			<template #default>
				<div class="flex flex-col gap-1">
					<div>{{ data.title }}</div>
					<p class="text-sm">$ {{ data.command }}</p>
				</div>
			</template>
			<template #mainExtra>
				<div class="flex flex-wrap items-center gap-3">
					<Badge
						type="splitted"
						:color="
							data.result === 'failed'
								? 'danger'
								: data.result === 'not applicable'
									? 'warning'
									: 'success'
						"
						class="uppercase"
					>
						<template #label>
							{{ data.result }}
						</template>
					</Badge>

					<Badge type="splitted" color="primary">
						<template #label>Compliance</template>
						<template #value>
							{{ data.compliance?.length || "-" }}
						</template>
					</Badge>

					<Badge type="splitted" color="primary">
						<template #label>Condition</template>
						<template #value>
							{{ data.condition || "-" }}
						</template>
					</Badge>

					<Badge type="splitted" color="primary">
						<template #label>Rules</template>
						<template #value>
							{{ data.rules?.length || "-" }}
						</template>
					</Badge>
				</div>
			</template>
		</CardEntity>
		<n-modal
			v-model:show="showDetails"
			preset="card"
			content-class="p-0!"
			:style="{ maxWidth: 'min(900px, 90vw)', minHeight: 'min(600px, 90vh)', overflow: 'hidden' }"
			:title="data?.title"
			:bordered="false"
			segmented
		>
			<ScaResultItemDetails :data="data" />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { ScaPolicyResult } from "@/types/agents.d"
import { NButton, NModal } from "naive-ui"
import { ref } from "vue"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import ScaResultItemDetails from "./ScaResultItemDetails.vue"

const { data, embedded } = defineProps<{
	data: ScaPolicyResult
	embedded?: boolean
}>()

const DetailsIcon = "carbon:settings-adjust"
const showDetails = ref(false)
</script>
