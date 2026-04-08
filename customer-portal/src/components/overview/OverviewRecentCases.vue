<template>
	<n-card
		title="Recent Cases"
		segmented
		:content-class="`flex flex-col gap-4 overflow-hidden ${!recentCases.length ? 'items-center justify-center' : 'p-0!'}`"
	>
		<n-empty v-if="!recentCases.length" description="No recent cases" />

		<n-scrollbar v-else class="flex grow" trigger="none">
			<div class="flex flex-col gap-4 p-4">
				<RecentCaseCard v-for="caseData in recentCases" :key="caseData.id" embedded :case-data />
			</div>
		</n-scrollbar>

		<n-button :text="!!recentCases.length" class="mb-4!" @click="goToCases()">
			<template #icon>
				<Icon name="carbon:launch" />
			</template>
			View all cases
		</n-button>
	</n-card>
</template>

<script setup lang="ts">
import type { DashboardCase } from "./types"
import { NButton, NCard, NEmpty, NScrollbar } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import { useNavigation } from "@/composables/common/useNavigation"
import RecentCaseCard from "./RecentCaseCard.vue"

defineProps<{
	recentCases: DashboardCase[]
}>()

const { routeCasesList } = useNavigation()

function goToCases() {
	routeCasesList().navigate()
}
</script>
