<template>
	<n-card size="small">
		<div class="@container flex flex-col gap-6">
			<n-form-item label="Overall verdict" :show-feedback="false">
				<n-radio-group v-model:value="form.overall_verdict">
					<n-radio-button value="up">
						<Icon :name="ThumbUpIcon" :size="14" class="mr-1" />
						Good
					</n-radio-button>
					<n-radio-button value="down">
						<Icon :name="ThumbDownIcon" :size="14" class="mr-1" />
						Bad
					</n-radio-button>
				</n-radio-group>
			</n-form-item>

			<!-- Template choice -->
			<n-form-item label="Template used" :show-feedback="false">
				<div v-if="report.report_markdown === null" class="text-secondary mb-1 text-sm">
					No template recorded on this report.
				</div>
				<n-radio-group v-model:value="form.template_choice">
					<n-radio value="correct">Correct template</n-radio>
					<n-radio value="partial">Partially correct</n-radio>
					<n-radio value="wrong">Wrong template</n-radio>
				</n-radio-group>
			</n-form-item>

			<!-- Ratings -->
			<div class="grid grid-cols-1 gap-6 @xl:grid-cols-3">
				<n-form-item label="Instructions quality" :show-feedback="false">
					<n-slider v-model:value="form.rating_instructions" :min="1" :max="5" :step="1" :marks="rateMarks" />
				</n-form-item>

				<n-form-item label="Artifact collection" :show-feedback="false">
					<n-slider v-model:value="form.rating_artifacts" :min="1" :max="5" :step="1" :marks="rateMarks" />
				</n-form-item>

				<n-form-item label="Severity assessment" :show-feedback="false">
					<n-slider v-model:value="form.rating_severity" :min="1" :max="5" :step="1" :marks="rateMarks" />
				</n-form-item>
			</div>

			<!-- Missing steps -->
			<n-form-item label="Missing steps" :show-feedback="false">
				<n-input
					v-model:value="form.missing_steps"
					type="textarea"
					placeholder="What investigation steps were missed?"
					:autosize="{ minRows: 2, maxRows: 6 }"
				/>
			</n-form-item>

			<!-- Suggested edits -->
			<n-form-item label="Suggested prompt / template edits" :show-feedback="false">
				<n-input
					v-model:value="form.suggested_edits"
					type="textarea"
					placeholder="How should the template or prompt be improved?"
					:autosize="{ minRows: 2, maxRows: 6 }"
				/>
			</n-form-item>
		</div>
	</n-card>
</template>

<script setup lang="ts">
import type { AiAnalystReport } from "@/types/aiAnalyst.d"
import { NCard, NFormItem, NInput, NRadio, NRadioButton, NRadioGroup, NSlider } from "naive-ui"
import { toRefs } from "vue"
import Icon from "@/components/common/Icon.vue"

export interface FormState {
	overall_verdict: "up" | "down" | null
	template_choice: "correct" | "wrong" | "partial" | null
	rating_instructions: number
	rating_artifacts: number
	rating_severity: number
	missing_steps: string
	suggested_edits: string
}

const props = defineProps<{
	report: AiAnalystReport
}>()

const { report } = toRefs(props)

const form = defineModel<FormState>("form", {
	default: {
		overall_verdict: null,
		template_choice: null,
		rating_instructions: 3,
		rating_artifacts: 3,
		rating_severity: 3,
		missing_steps: "",
		suggested_edits: ""
	}
})

const ThumbUpIcon = "mdi:thumb-up-outline"
const ThumbDownIcon = "mdi:thumb-down-outline"

const rateMarks = { 1: "1", 2: "2", 3: "3", 4: "4", 5: "5" }
</script>
