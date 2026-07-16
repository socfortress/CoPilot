<template>
	<div class="page flex flex-col gap-4">
		<DetailPageHeader :title="software?.name" :back-route="routeAlertsMitre()">
			<template v-if="software" #meta>
				<span class="text-secondary font-mono text-sm">{{ software.external_id }}</span>
			</template>
		</DetailPageHeader>

		<SoftwareOverview v-if="softwareId" :id="softwareId" :key="softwareId" full-width @loaded="software = $event" />
		<n-empty v-else description="Invalid MITRE software ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import type { MitreSoftwareDetails } from "@/types/mitre"
import { NEmpty } from "naive-ui"
import { ref, watch } from "vue"
import DetailPageHeader from "@/components/common/DetailPageHeader.vue"
import SoftwareOverview from "@/components/mitre/Software/SoftwareOverview.vue"
import { useNavigation, useRouteParam } from "@/composables/useNavigation"

const { routeAlertsMitre } = useNavigation()

const software = ref<MitreSoftwareDetails | null>(null)

const softwareId = useRouteParam("softwareId")

watch(softwareId, () => {
	software.value = null
})
</script>
