<template>
	<div class="flex flex-col gap-4 md:flex-row">
		<div class="flex grow flex-col gap-3">
			<CardKV>
				<template #key>id</template>
				<template #value>
					<span class="whitespace-pre-wrap">
						{{ entity.id ?? "—" }}
					</span>
				</template>
			</CardKV>
			<CardKV>
				<template #key>name</template>
				<template #value>
					<span class="whitespace-pre-wrap">
						{{ entity.name ?? "—" }}
					</span>
				</template>
			</CardKV>
			<CardKV v-if="entity.description" class="[&_p]:text-white">
				<template #key>description</template>
				<template #value>
					<Markdown :source="entity.description" />
				</template>
			</CardKV>

			<CardKV v-if="entity.references?.length">
				<template #key>references</template>
				<template #value>
					<References :references="entity.references" />
				</template>
			</CardKV>
		</div>
		<StickySidebar>
			<n-card content-class="bg-secondary flex flex-col gap-3 rounded-lg" size="small">
				<div class="flex flex-col gap-0.5 text-sm">
					<div class="text-secondary font-mono text-xs">external_id</div>
					<div>{{ entity.external_id }}</div>
				</div>
				<div class="flex flex-col gap-0.5 text-sm">
					<div class="text-secondary font-mono text-xs">created_time</div>
					<div>{{ formatDate(entity.created_time, dFormats.datetime) }}</div>
				</div>
				<div class="flex flex-col gap-0.5 text-sm">
					<div class="text-secondary font-mono text-xs">modified_time</div>
					<div>{{ formatDate(entity.modified_time, dFormats.datetime) }}</div>
				</div>
				<div class="flex flex-col gap-0.5 text-sm">
					<div class="text-secondary font-mono text-xs">url</div>
					<div>
						<a :href="entity.url" target="_blank" rel="nofollow noopener noreferrer">
							{{ entity.url }}
						</a>
					</div>
				</div>
				<div class="flex flex-col gap-0.5 text-sm">
					<div class="text-secondary font-mono text-xs">source</div>
					<div>{{ entity.source }}</div>
				</div>
				<div class="flex flex-col gap-0.5 text-sm">
					<div class="text-secondary font-mono text-xs">type</div>
					<div>{{ entity.type || "—" }}</div>
				</div>
				<div class="flex flex-col gap-0.5 text-sm">
					<div class="text-secondary font-mono text-xs">mitre_version</div>
					<div>{{ entity.mitre_version }}</div>
				</div>
				<div class="flex flex-col gap-0.5 text-sm">
					<div class="text-secondary font-mono text-xs">platforms</div>
					<div class="mt-0.5 flex flex-wrap gap-1">
						<template v-if="!entity.platforms?.length">—</template>
						<template v-else>
							<code v-for="item of entity.platforms" :key="item" class="text-xs">
								{{ item }}
							</code>
						</template>
					</div>
				</div>
				<div class="flex flex-col gap-0.5 text-sm">
					<div class="text-secondary font-mono text-xs">aliases</div>
					<div class="mt-0.5 flex flex-wrap gap-1">
						<template v-if="!entity.aliases?.length">—</template>
						<template v-else>
							<code v-for="item of entity.aliases" :key="item" class="text-xs">
								{{ item }}
							</code>
						</template>
					</div>
				</div>
			</n-card>

			<div class="flex flex-wrap gap-1">
				<Badge v-if="entity.deprecated" color="primary" class="font-mono text-xs!">
					<template #value>deprecated</template>
				</Badge>
			</div>
		</StickySidebar>
	</div>
</template>

<script setup lang="ts">
import type { MitreSoftwareDetails } from "@/types/mitre"
import { NCard } from "naive-ui"
import Badge from "@/components/common/Badge.vue"
import CardKV from "@/components/common/cards/CardKV.vue"
import Markdown from "@/components/common/Markdown.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"
import References from "../common/References.vue"
import StickySidebar from "../common/StickySidebar.vue"

defineProps<{
	entity: MitreSoftwareDetails
}>()

const dFormats = useSettingsStore().dateFormat
</script>
