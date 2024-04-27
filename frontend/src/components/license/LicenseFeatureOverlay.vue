<template>
	<div class="over-layer feature-layer" v-if="showBanner">
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
import { ref } from "vue"
import { NAlert, NButton } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import Api from "@/api"
import { onBeforeMount } from "vue"
import type { LicenseFeatures } from "@/types/license"
import { useGoto } from "@/composables/useGoto"

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
