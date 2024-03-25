<template>
	<div class="flex flex-col gap-8">
		<div class="flex gap-6 mb-2">
			<n-avatar :size="110" :src="logo" />

			<div class="flex flex-col justify-between grow">
				<ImageCropper v-slot="{ openCropper }" @crop="setCroppedImage" :placeholder="'Select a Logo'">
					<n-button @click="openCropper()">
						<template #icon>
							<Icon :name="EditIcon"></Icon>
						</template>
						Edit Logo Image
					</n-button>
				</ImageCropper>

				<n-form-item label="Company" :show-feedback="false">
					<n-input v-model:value="company" placeholder="Insert you company name" />
				</n-form-item>
			</div>
		</div>

		<div class="theme">
			<n-form-item label="Theme" feedback="⊙ choose panels palette">
				<n-radio-group v-model:value="theme">
					<n-radio-button value="light">Light</n-radio-button>
					<n-radio-button value="dark">Dark</n-radio-button>
				</n-radio-group>
			</n-form-item>
		</div>

		<div class="retina">
			<n-form-item label="Retina" feedback="⊙ improve panels resolution; it will increase the report size">
				<n-switch v-model:value="retina" />
			</n-form-item>
		</div>
	</div>
</template>

<script setup lang="ts">
import { watch, onMounted } from "vue"
import { NAvatar, NButton, NInput, NFormItem, NRadioGroup, NRadioButton, NSwitch } from "naive-ui"
import ImageCropper, { type ImageCropperResult } from "@/components/common/ImageCropper.vue"
import Icon from "@/components/common/Icon.vue"
import { useStorage } from "@vueuse/core"
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
