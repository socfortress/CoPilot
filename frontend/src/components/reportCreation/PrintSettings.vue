<template>
	<div class="flex flex-col gap-8">
		<div class="mb-2 flex gap-6">
			<n-avatar :size="110" :src="logo" />

			<div class="flex grow flex-col justify-between">
				<ImageCropper v-slot="{ openCropper }" placeholder="Select a Logo" @crop="setCroppedImage">
					<n-button @click="openCropper()">
						<template #icon>
							<Icon :name="EditIcon" />
						</template>
						Edit Logo Image
					</n-button>
				</ImageCropper>

				<n-form-item label="Company" :show-feedback="false">
					<n-input v-model:value="company" placeholder="Insert you company name" />
				</n-form-item>
			</div>
		</div>

		<div class="flex flex-col gap-2">
			<n-form-item label="Theme" :show-feedback="false">
				<n-radio-group v-model:value="theme">
					<n-radio-button value="light">Light</n-radio-button>
					<n-radio-button value="dark">Dark</n-radio-button>
				</n-radio-group>
			</n-form-item>
			<div class="text-secondary text-sm">⊙ choose panels palette</div>
		</div>

		<div class="flex flex-col gap-2">
			<n-form-item label="Retina" :show-feedback="false">
				<n-switch v-model:value="retina" />
			</n-form-item>
			<div class="text-secondary text-sm">⊙ improve panels resolution; it will increase the report size</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { ImageCropperResult } from "@/components/common/ImageCropper.vue"
import { useStorage } from "@vueuse/core"
import { NAvatar, NButton, NFormItem, NInput, NRadioButton, NRadioGroup, NSwitch } from "naive-ui"
import { onMounted, watch } from "vue"
import Icon from "@/components/common/Icon.vue"
import ImageCropper from "@/components/common/ImageCropper.vue"
import * as defaultSettings from "./defaultSettings"

export interface PrintSettingsData {
	logo: string
	company: string
	theme: "light" | "dark"
	retina: boolean
}

const emit = defineEmits<{
	(e: "update", value: PrintSettingsData): void
}>()

const EditIcon = "uil:image-edit"

const logo = useStorage<string>("report-settings-logo", defaultSettings.logo, localStorage)
const company = useStorage<string>("report-settings-company", defaultSettings.company, localStorage)
const theme = useStorage<"light" | "dark">("report-settings-theme", defaultSettings.theme, localStorage)
const retina = useStorage<boolean>("report-settings-retina", defaultSettings.retina, localStorage)

watch([logo, company, theme, retina], () => {
	emitData()
})

function setCroppedImage(result: ImageCropperResult) {
	const canvas = result.canvas as HTMLCanvasElement
	logo.value = canvas.toDataURL()
}

function emitData() {
	emit("update", {
		logo: logo.value,
		company: company.value,
		theme: theme.value,
		retina: retina.value
	})
}

onMounted(() => {
	emitData()
})
</script>
