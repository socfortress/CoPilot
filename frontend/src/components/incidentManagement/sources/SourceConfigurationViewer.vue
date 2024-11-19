<template>
	<div v-if="sourceConfiguration" class="flex flex-col gap-3">
		<CardKV v-if="showSource">
			<template #key>Source</template>
			<template #value>
				{{ sourceConfiguration.source }}
			</template>
		</CardKV>
		<CardKV>
			<template #key>Field names</template>
			<template #value>
				<div class="flex flex-wrap gap-2">
					<Badge v-for="field of sourceConfiguration.field_names" :key="field" type="splitted" fluid>
						<template #value>
							{{ field }}
						</template>
					</Badge>
				</div>
			</template>
		</CardKV>
		<CardKV>
			<template #key>IOC Field names</template>
			<template #value>
				<div v-if="sourceConfiguration.ioc_field_names?.length" class="flex flex-wrap gap-2">
					<Badge v-for="field of sourceConfiguration.ioc_field_names" :key="field" type="splitted" fluid>
						<template #value>
							{{ field }}
						</template>
					</Badge>
				</div>
				<span v-else>-</span>
			</template>
		</CardKV>
		<CardKV>
			<template #key>Asset name</template>
			<template #value>
				{{ sourceConfiguration.asset_name }}
			</template>
		</CardKV>
		<CardKV>
			<template #key>Timefield name</template>
			<template #value>
				{{ sourceConfiguration.timefield_name }}
			</template>
		</CardKV>
		<CardKV>
			<template #key>Alert title name</template>
			<template #value>
				{{ sourceConfiguration.alert_title_name }}
			</template>
		</CardKV>
	</div>
</template>

<script setup lang="ts">
import type { SourceConfiguration } from "@/types/incidentManagement/sources.d"
import Badge from "@/components/common/Badge.vue"
import CardKV from "@/components/common/cards/CardKV.vue"

const { sourceConfiguration, showSource } = defineProps<{
	sourceConfiguration: SourceConfiguration
	showSource?: boolean
}>()
</script>
