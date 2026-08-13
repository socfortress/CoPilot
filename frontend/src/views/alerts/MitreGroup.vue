<template>
	<div class="page flex flex-col gap-4">
		<DetailPageHeader :title="group?.name" :back-route="routeAlertsMitre()">
			<template v-if="group" #meta>
				<span class="text-secondary font-mono text-sm">{{ group.external_id }}</span>
			</template>
		</DetailPageHeader>

		<GroupOverview v-if="groupId" :id="groupId" :key="groupId" full-width @loaded="group = $event" />
		<n-empty v-else description="Invalid MITRE group ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import type { MitreGroupDetails } from "@/types/mitre"
import { NEmpty } from "naive-ui"
import { ref, watch } from "vue"
import DetailPageHeader from "@/components/common/DetailPageHeader.vue"
import GroupOverview from "@/components/mitre/Group/GroupOverview.vue"
import { useNavigation, useRouteParam } from "@/composables/useNavigation"

const { routeAlertsMitre } = useNavigation()

const group = ref<MitreGroupDetails | null>(null)

const groupId = useRouteParam("groupId")

watch(groupId, () => {
	group.value = null
})
</script>
