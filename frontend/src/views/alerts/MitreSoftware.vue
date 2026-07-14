<template>
	<div class="page flex flex-col gap-4">
		<div class="flex min-w-0 items-center gap-4">
			<n-button quaternary class="shrink-0" @click="goBack(routeAlertsMitre())">
				<template #icon>
					<Icon :name="BackIcon" />
				</template>
				Back
			</n-button>

			<div v-if="software" class="flex min-w-0 flex-wrap items-baseline gap-2">
				<span class="truncate text-lg font-semibold">{{ software.name }}</span>
				<span class="text-secondary font-mono text-sm">{{ software.external_id }}</span>
			</div>
		</div>

		<SoftwareOverview v-if="softwareId" :id="softwareId" :key="softwareId" full-width @loaded="software = $event" />
		<n-empty v-else description="Invalid MITRE software ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import type { MitreSoftwareDetails } from "@/types/mitre"
import { NButton, NEmpty } from "naive-ui"
import { ref, watch } from "vue"
import Icon from "@/components/common/Icon.vue"
import SoftwareOverview from "@/components/mitre/Software/SoftwareOverview.vue"
import { useNavigation, useRouteParam } from "@/composables/useNavigation"

const { goBack, routeAlertsMitre } = useNavigation()

const BackIcon = "carbon:arrow-left"
const software = ref<MitreSoftwareDetails | null>(null)

const softwareId = useRouteParam("softwareId")

watch(softwareId, () => {
	software.value = null
})
</script>
