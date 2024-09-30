<template>
	<img
		v-if="isImageError && fallback"
		:src="fallback"
		:alt="props.alt"
		class="image-fallback"
		draggable="false"
		:class="imageClass"
		@load="imageFallback"
	/>
	<img
		v-if="!isImageError"
		:src="mainSrc"
		:alt="props.alt"
		draggable="false"
		class="image-loading"
		:class="imageClass"
		@load="imageLoading"
	/>
</template>

<script setup lang="ts">
import { ref, watch } from "vue"

export interface ImageEvent {
	height: number
}
export interface ImageLoadEvent extends Event {
	path?: HTMLElement[]
}

const props = defineProps({
	src: {
		type: String,
		required: true
	},
	fallback: {
		type: String
	},
	loading: {
		type: String
	},
	imageClass: {
		type: String,
		default: ""
	},
	alt: {
		type: String,
		default: ""
	}
})

const emit = defineEmits(["image-error", "image-loading", "image-loaded", "image-fallback"])

const isImageLoaded = ref(false)
const isImageError = ref(false)
const mainSrc = ref(props.loading)

function imageLoading(e: ImageLoadEvent) {
	const elPath: HTMLElement | undefined = e.path && e.path[0]
	const el = (e.target || elPath || null) as HTMLImageElement | null

	emit("image-loading", { height: el?.offsetHeight || 0 } as ImageEvent)
	return e
}
function imageFallback(e: ImageLoadEvent) {
	const elPath: HTMLElement | undefined = e.path && e.path[0]
	const el = (e.target || elPath || null) as HTMLImageElement | null

	emit("image-fallback", { height: el?.offsetHeight || 0 } as ImageEvent)
	return e
}
function imageLoaded(e: ImageLoadEvent) {
	mainSrc.value = props.src
	const elPath: HTMLElement | undefined = e.path && e.path[0]
	const el = (e.target || elPath || null) as HTMLImageElement | null
	isImageLoaded.value = true

	emit("image-loaded", { height: el?.offsetHeight || 0 } as ImageEvent)
}
function imageError() {
	isImageError.value = true
	emit("image-error")
}

function createLoader() {
	const img = new Image()
	img.onload = imageLoaded
	img.onerror = imageError
	img.src = props.src
}

watch(
	() => props.src,
	() => {
		createLoader()
	}
)

createLoader()
</script>

<style lang="scss" scoped>
img {
	opacity: 1;
	display: block;
	transition: opacity 0.8s;

	&.hide {
		opacity: 0;
		max-height: 0;
		//transform: scale(0);
	}
}
</style>
