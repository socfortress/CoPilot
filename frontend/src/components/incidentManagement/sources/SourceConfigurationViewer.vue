<template>
	<div v-if="sourceConfiguration" class="flex flex-col gap-3">
		<KVCard v-if="showSource">
			<template #key>Source</template>
			<template #value>
				{{ sourceConfiguration.source }}
			</template>
		</KVCard>
		<KVCard>
			<template #key>Field names</template>
			<template #value>
				<div class="flex flex-wrap gap-2">
					<Badge type="splitted" v-for="field of sourceConfiguration.field_names" :key="field" fluid>
						<template #value>
							{{ field }}
						</template>
					</Badge>
				</div>
			</template>
		</KVCard>
		<KVCard>
			<template #key>Asset name</template>
			<template #value>
				{{ sourceConfiguration.asset_name }}
			</template>
		</KVCard>
		<KVCard>
			<template #key>Timefield name</template>
			<template #value>
				{{ sourceConfiguration.timefield_name }}
			</template>
		</KVCard>
		<KVCard>
			<template #key>Alert title name</template>
			<template #value>
				{{ sourceConfiguration.alert_title_name }}
			</template>
		</KVCard>
	</div>
</template>

<script setup lang="ts">
import Badge from "@/components/common/Badge.vue"
import KVCard from "@/components/common/KVCard.vue"
import type { SourceConfiguration } from "@/types/incidentManagement/sources.d"

const { sourceConfiguration, showSource } = defineProps<{
	sourceConfiguration: SourceConfiguration
	showSource?: boolean
}>()
</script>
