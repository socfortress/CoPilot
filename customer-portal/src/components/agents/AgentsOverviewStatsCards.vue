<template>
	<n-spin :show="loading">
		<div class="grid grid-cols-1 gap-6 @xl:grid-cols-2 @4xl:grid-cols-4">
			<CardStats data-testid="stat-total" title="Total" :value="stats.total">
				<template #icon>
					<Icon :name="ICONS.agents" :size="24" class="text-info" />
				</template>
			</CardStats>

			<CardStats data-testid="stat-active" title="Active" :value="stats.active">
				<template #icon>
					<Icon name="carbon:checkmark-outline" :size="24" class="text-success" />
				</template>
			</CardStats>

			<CardStats data-testid="stat-critical" title="Critical" :value="stats.critical">
				<template #icon>
					<Icon name="carbon:warning-alt" :size="24" class="text-warning" />
				</template>
			</CardStats>

			<CardStats data-testid="stat-offline" title="Offline" :value="stats.offline">
				<template #icon>
					<Icon name="carbon:close-outline" :size="24" class="text-error" />
				</template>
			</CardStats>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { AgentsStats } from "@/types/agents"
import { NSpin } from "naive-ui"
import CardStats from "@/components/common/cards/CardStats.vue"
import Icon from "@/components/common/Icon.vue"
import { ICONS } from "@/const"

const { stats } = defineProps<{
	stats: AgentsStats
	loading: boolean
}>()
</script>
