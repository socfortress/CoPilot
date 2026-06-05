<template>
	<div class="h-full">
		<CardEntity
			size="small"
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
				<p class="text-default line-clamp-2 text-sm leading-snug font-semibold">
					{{ policy.name }}
				</p>
			</template>

			<template #headerExtra>
				<PlatformBadge :platform="policy.platform" size="small" />
			</template>

			<template #default>
				<p class="text-secondary line-clamp-3 text-xs leading-relaxed">
					{{ policy.description }}
				</p>
			</template>

			<template #footerMain>
				<div class="flex flex-wrap items-center gap-2">
					<Badge type="splitted" bright size="small">
						<template #label>CIS</template>
						<template #value>{{ policy.cis_version }}</template>
					</Badge>
					<Badge type="splitted" bright size="small" color="primary">
						<template #label>Version</template>
						<template #value>{{ policy.app_version }}</template>
					</Badge>
					<Badge type="splitted" size="small">
						<template #label>App</template>
						<template #value>{{ policy.application }}</template>
					</Badge>
				</div>
			</template>

			<template #footerExtra>
				<div class="text-secondary flex min-w-0 items-center gap-1.5 text-xs">
					<Icon :name="FileIcon" :size="14" class="shrink-0" />
					<span class="truncate font-mono" :title="fileName">{{ fileName }}</span>
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
import { computed, ref } from "vue"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import PlatformBadge from "@/components/common/PlatformBadge.vue"
import PolicyCardContent from "./PolicyCardContent.vue"

const { policy } = defineProps<{ policy: ScaPolicyItem; embedded?: boolean }>()

const showDetails = ref(false)
const FileIcon = "carbon:document"

const fileName = computed(() => policy.file.split("/").pop() ?? policy.file)
</script>
