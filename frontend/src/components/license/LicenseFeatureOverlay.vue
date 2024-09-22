<template>
	<div v-if="showBanner" class="over-layer feature-layer">
		<n-alert title="Feature required">
			<template #icon>
				<Icon :name="AlertIcon" :size="18"></Icon>
			</template>
			<div class="flex flex-col gap-4">
				<div>
					It seems that the feature you are looking for is currently unavailable. To unlock and use it, you
					need to enable this feature. You can manage your features from the License page.
				</div>
				<div class="flex justify-end">
					<n-button @click="gotoLicense()">
						<template #icon>
							<Icon :name="LicenseIcon"></Icon>
						</template>
						View license
					</n-button>
				</div>
			</div>
		</n-alert>
	</div>
</template>

<script setup lang="ts">
import type { LicenseFeatures } from "@/types/license.d"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useGoto } from "@/composables/useGoto"
import { NAlert, NButton } from "naive-ui"
import { onBeforeMount, ref } from "vue"

const { feature } = defineProps<{ feature: LicenseFeatures }>()

const LicenseIcon = "carbon:license"
const AlertIcon = "mdi:alert-outline"

const { gotoLicense } = useGoto()
const showBanner = ref(false)

function checkFeature(feature: LicenseFeatures) {
	Api.license
		.isFeatureEnabled(feature)
		.then(res => {
			if (!res.data.success) {
				showBanner.value = true
			}
		})
		.catch(() => {
			showBanner.value = true
		})
}

onBeforeMount(() => {
	checkFeature(feature)
})
</script>
