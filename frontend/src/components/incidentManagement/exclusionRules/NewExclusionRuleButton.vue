<template>
	<div>
		<n-button size="small" type="primary" @click="showForm = true">
			<template #icon>
				<Icon :name="NewNewExclusionRuleIcon" :size="15"></Icon>
			</template>
			Create Exclusion Rule
		</n-button>

		<n-modal
			v-model:show="showForm"
			display-directive="show"
			preset="card"
			:style="{ maxWidth: 'min(600px, 90vw)', minHeight: 'min(200px, 90vh)', overflow: 'hidden' }"
			title="Create Exclusion Rule"
			:bordered="false"
			content-class="flex flex-col"
			segmented
		>
			<ExclusionRuleForm reset-on-submit @submitted="submitted()" @mounted="formCTX = $event" />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import Icon from "@/components/common/Icon.vue"
import { NButton, NModal } from "naive-ui"
import { ref, watch } from "vue"
import ExclusionRuleForm from "./ExclusionRuleForm.vue"

const emit = defineEmits<{
	(e: "success"): void
}>()

const NewNewExclusionRuleIcon = "carbon:add-alt"
const showForm = ref(false)
const formCTX = ref<{ reset: () => void } | null>(null)

function submitted() {
	emit("success")
	showForm.value = false
}

watch(showForm, val => {
	if (val) {
		formCTX.value?.reset()
	}
})
</script>
