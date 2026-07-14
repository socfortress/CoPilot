<template>
	<div class="page flex flex-col gap-4">
		<div class="flex min-w-0 items-center gap-4">
			<n-button quaternary class="shrink-0" @click="goBack(routeAlertsMitre())">
				<template #icon>
					<Icon :name="BackIcon" />
				</template>
				Back
			</n-button>

			<div v-if="group" class="flex min-w-0 flex-wrap items-baseline gap-2">
				<span class="truncate text-lg font-semibold">{{ group.name }}</span>
				<span class="text-secondary font-mono text-sm">{{ group.external_id }}</span>
			</div>
		</div>

		<GroupOverview v-if="groupId" :id="groupId" :key="groupId" full-width @loaded="group = $event" />
		<n-empty v-else description="Invalid MITRE group ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import type { MitreGroupDetails } from "@/types/mitre"
import { NButton, NEmpty } from "naive-ui"
import { ref, watch } from "vue"
import Icon from "@/components/common/Icon.vue"
import GroupOverview from "@/components/mitre/Group/GroupOverview.vue"
import { useNavigation, useRouteParam } from "@/composables/useNavigation"

const { goBack, routeAlertsMitre } = useNavigation()

const BackIcon = "carbon:arrow-left"
const group = ref<MitreGroupDetails | null>(null)

const groupId = useRouteParam("groupId")

watch(groupId, () => {
	group.value = null
})
</script>
