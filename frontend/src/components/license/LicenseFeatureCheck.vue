<template>
	<div>
		<n-tooltip v-if="feedback === 'tooltip'" to="body" :disabled="!showFeedback">
			<template #trigger>
				<slot v-if="$slots.default" />
				<template v-else>
					<Icon v-if="showFeedback" :name="LockIcon" :size="18" />
					<span v-else></span>
				</template>
			</template>
			<div class="w-90vw flex !max-w-lg flex-col gap-3">
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
		</n-tooltip>

		<div v-if="showFeedback && feedback === 'overlay'" class="over-layer animate-fade">
			<n-card class="w-90vw !max-w-lg">
				<template #header>
					<div class="flex items-center gap-3">
						<Icon :name="AlertIcon" :size="18" />
						<span>Feature required</span>
					</div>
				</template>
				<div>
					It seems that the feature you are looking for is currently unavailable. To unlock and use it, you
					need to enable this feature. You can manage your features from the License page.
				</div>
				<template #footer>
					<div class="flex justify-end">
						<n-button @click="gotoLicense()">
							<template #icon>
								<Icon :name="LicenseIcon"></Icon>
							</template>
							View license
						</n-button>
					</div>
				</template>
			</n-card>
		</div>

		<n-modal v-model:show="showModal" class="w-90vw !max-w-lg" preset="card">
			<template #header>
				<div class="flex items-center gap-3">
					<Icon :name="AlertIcon" :size="18" />
					<span>Feature required</span>
				</div>
			</template>
			<div>
				It seems that the feature you are looking for is currently unavailable. To unlock and use it, you need
				to enable this feature. You can manage your features from the License page.
			</div>
			<template #footer>
				<div class="flex justify-end">
					<n-button @click="gotoLicense()">
						<template #icon>
							<Icon :name="LicenseIcon"></Icon>
						</template>
						View license
					</n-button>
				</div>
			</template>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { LicenseFeatures } from "@/types/license.d"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useGoto } from "@/composables/useGoto"
import { NButton, NCard, NModal, NTooltip } from "naive-ui"
import { ref, watch, watchEffect } from "vue"

const { feature, feedback, disabled, forceShowFeedback } = defineProps<{
	feature: LicenseFeatures
	feedback?: "overlay" | "alert" | "tooltip"
	disabled?: boolean
	forceShowFeedback?: boolean
}>()

const emit = defineEmits<{
	(e: "response", value: boolean): void
	(e: "startLoading"): void
	(e: "stopLoading"): void
}>()

const LockIcon = "carbon:locked"
const LicenseIcon = "carbon:license"
const AlertIcon = "mdi:alert-outline"
const loading = ref(false)
const { gotoLicense } = useGoto()
const showFeedback = ref(forceShowFeedback ?? false)
const showModal = ref(false)

function checkFeature(feature: LicenseFeatures) {
	loading.value = true

	Api.license
		.isFeatureEnabled(feature)
		.then(res => {
			if (!res.data.success) {
				showFeedback.value = true
				emit("response", false)
			} else {
				emit("response", true)
			}
		})
		.catch(() => {
			showFeedback.value = true
			emit("response", false)
		})
		.finally(() => {
			loading.value = false
		})
}

watch(showFeedback, val => {
	if (val && feedback === "alert") {
		showModal.value = true
	}
})

watch(loading, val => {
	if (val) {
		emit("startLoading")
	} else {
		emit("stopLoading")
	}
})

watch(
	[() => disabled, () => feature],
	values => {
		if (!values[0]) {
			checkFeature(values[1])
		}
	},
	{ immediate: true }
)

watchEffect(() => {
	showFeedback.value = forceShowFeedback ?? false
})
</script>
