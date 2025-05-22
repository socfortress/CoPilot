<template>
	<div class="soc-notes-list">
		<div class="px-7 pt-4">
			<n-input v-model:value="notesFilter" placeholder="Search notes..." clearable />
		</div>
		<n-spin :show="loadingNotes" class="min-h-28">
			<div v-if="notesList?.length" class="flex flex-col gap-2 p-7 pt-3" style="container-type: inline-size">
				<SocCaseNote v-for="note of notesList" :key="note.note_id" :note="note" />
			</div>
			<template v-else>
				<n-empty v-if="!loadingNotes" description="No items found" class="h-48 justify-center" />
			</template>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { SocNote } from "@/types/soc/note.d"
import { refDebounced } from "@vueuse/core"
import axios from "axios"
import { NEmpty, NInput, NSpin, useMessage } from "naive-ui"
import { onBeforeMount, ref, toRefs, watch } from "vue"
import Api from "@/api"
import SocCaseNote from "./SocCaseNote.vue"

const props = defineProps<{ caseId: string | number }>()

const requested = defineModel<boolean | undefined>("requested", { default: false })

const { caseId } = toRefs(props)

const loadingNotes = ref(false)
const message = useMessage()
const notesFilter = ref("")
const notesFilterDebounced = refDebounced(notesFilter, 1000)
let abortControllerNotes: AbortController | null = null

const notesList = ref<SocNote[] | null>(null)

function getNotes() {
	loadingNotes.value = true

	abortControllerNotes = new AbortController()

	Api.soc
		.getNotesByCase(
			caseId.value.toString(),
			{ searchTerm: notesFilterDebounced.value || "" },
			abortControllerNotes.signal
		)
		.then(res => {
			if (res.data.success) {
				notesList.value = res.data?.notes || null
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			if (!axios.isCancel(err)) {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			}
		})
		.finally(() => {
			loadingNotes.value = false
		})
}

watch(notesFilterDebounced, () => {
	if (abortControllerNotes !== null) {
		abortControllerNotes?.abort()
	}

	setTimeout(() => {
		getNotes()
	}, 300)
})

watch(requested, val => {
	if (val) {
		getNotes()
	}

	requested.value = false
})

onBeforeMount(() => {
	getNotes()
	abortControllerNotes?.abort()
})
</script>
