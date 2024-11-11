<template>
	<div class="image-cropper">
		<slot :open-cropper="openCropper" />

		<n-modal v-model:show="showCropper">
			<n-card class="image-cropper-modal flex flex-col" content-class="!p-5">
				<div class="aspect-square">
					<div v-if="!img" class="upload-box">
						<n-upload v-show="!img" accept="image/*" :show-file-list="false" @change="setImage">
							<n-upload-dragger>
								<div>{{ placeholder }}</div>
							</n-upload-dragger>
						</n-upload>
					</div>
					<div v-if="img" class="crop-box">
						<Cropper
							ref="cropper"
							class="cropper aspect-square"
							:src="img"
							:stencil-size="stencilSize"
							:stencil-props="stencilProps"
							:resize-image="resizeImage"
							image-restriction="stencil"
							:stencil-component="stencil"
						/>
					</div>
				</div>
				<div class="mt-4 flex justify-end gap-4">
					<n-button secondary @click="closeCropper()">Close</n-button>
					<n-button v-if="img" type="primary" @click="emitCrop()">Save</n-button>
				</div>
			</n-card>
		</n-modal>
	</div>
</template>

<script lang="ts" setup>
import { NButton, NCard, NModal, NUpload, NUploadDragger, type UploadSettledFileInfo } from "naive-ui"
import { computed, ref, toRefs } from "vue"
import { CircleStencil, Cropper, type CropperResult, RectangleStencil } from "vue-advanced-cropper"
import "vue-advanced-cropper/dist/style.css"

export type ImageCropperResult = CropperResult

const { placeholder = "Select an image", shape = "square" } = defineProps<{
	placeholder?: string
	shape?: "square" | "circle"
}>()

const emit = defineEmits<{
	(e: "crop", value: ImageCropperResult): void
}>()

const stencil = computed(() => (shape === "circle" ? CircleStencil : RectangleStencil))
const img = ref("")
const showCropper = ref(false)
const cropper = ref<typeof Cropper | null>(null)

const stencilSize = ref({
	width: 300,
	height: 300
})
const stencilProps = ref({
	handlers: {},
	movable: false,
	scalable: false,
	aspectRatio: 1
})
const resizeImage = ref({
	adjustStencil: false
})

function closeCropper() {
	showCropper.value = false
	img.value = ""
}
function openCropper() {
	showCropper.value = true
	img.value = ""
}

function setImage(data: {
	file: UploadSettledFileInfo
	fileList: UploadSettledFileInfo[]
	event: ProgressEvent | Event | undefined
}): void {
	if (data?.file?.file) {
		const reader = new FileReader()
		reader.readAsDataURL(data.file.file)
		reader.onload = () => {
			img.value = reader.result?.toString() || ""
		}
	}
}

function emitCrop() {
	if (cropper.value) {
		const result = cropper.value.getResult()
		emit("crop", result)
	}
	closeCropper()
}
</script>

<style lang="scss" scoped>
.image-cropper-modal {
	width: 90vw;
	max-width: 300px;

	.upload-box {
		height: 100%;
		width: 100%;

		.n-upload {
			height: 100%;
			width: 100%;

			:deep() {
				.n-upload-trigger,
				.n-upload-dragger {
					height: 100%;
					width: 100%;
					display: flex;
					justify-content: center;
					align-items: center;
				}
			}
		}
	}

	.crop-box {
		overflow: hidden;
		border-radius: var(--border-radius-small);

		:deep() {
			.vue-line-wrapper {
				display: none;
			}
		}
	}
}
</style>
