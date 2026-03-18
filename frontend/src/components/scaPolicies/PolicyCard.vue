<template>
	<div class="h-full">
		<CardEntity
			hoverable
			clickable
			:embedded
			class="@container h-full"
			main-box-class="grow"
			card-entity-wrapper-class="h-full"
			header-box-class="flex-nowrap! items-start"
			@click.stop="showDetails = true"
		>
			<template #headerMain>
				<div class="flex flex-wrap items-center gap-2">
					<Badge type="splitted" size="small">
						<template #label>CIS</template>
						<template #value>{{ policy.cis_version }}</template>
					</Badge>
					<PlatformBadge :platform="policy.platform" />
				</div>
			</template>
			<template #headerExtra>
				<Badge size="small" color="primary">
					<template #value>{{ policy.app_version }}</template>
				</Badge>
			</template>
			<template #default>
				<div class="flex flex-col gap-2">
					<div class="font-semibold">{{ policy.name }}</div>
					<p class="line-clamp-3 text-sm">{{ policy.description }}</p>
				</div>
			</template>
			<template #mainExtra>
				<div class="flex flex-wrap items-center gap-2">
					<Badge type="splitted" size="small">
						<template #label>App</template>
						<template #value>{{ policy.application }}</template>
					</Badge>
				</div>
			</template>
		</CardEntity>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(600px, 90vh)', overflow: 'hidden' }"
			:title="policy.name"
			:bordered="false"
			segmented
		>
			<PolicyCardContent :policy />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { ScaPolicyItem } from "@/types/sca.d"
import { NModal } from "naive-ui"
import { ref } from "vue"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import PlatformBadge from "@/components/common/PlatformBadge.vue"
import PolicyCardContent from "./PolicyCardContent.vue"

defineProps<{ policy: ScaPolicyItem; embedded?: boolean }>()

const showDetails = ref(false)
</script>
