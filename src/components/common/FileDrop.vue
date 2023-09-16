<template>
	<form class="file-drop">
		<label>
			<slot></slot>
			<input type="file" :multiple="multiple" @change="onChange" :accept="accept" />
		</label>
	</form>
</template>

<script lang="ts" setup>
import { toRefs } from "vue"

defineOptions({
	name: "FileDrop"
})

const props = withDefaults(
	defineProps<{
		accept: string
		multiple: boolean
	}>(),
	{ accept: ".jpg,.jpeg,.png,.webp", multiple: false }
)
const { accept, multiple } = toRefs(props)

const emit = defineEmits<{
	(e: "change-file", value: FileList | File | null): void
}>()

function onChange(event: Event) {
	const input = event.target as HTMLInputElement
	if (multiple.value) {
		emit("change-file", input?.files)
	} else {
		if (input?.files?.length) {
			emit("change-file", input?.files[0])
		}
	}
	input?.form?.reset()
}
</script>

<style lang="scss" scoped>
.file-drop {
	label {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 100%;
		height: 100%;
		cursor: pointer;

		input {
			display: none;
		}
	}
}
</style>
