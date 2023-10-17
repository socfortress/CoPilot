<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Progress</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/progress"
					target="_blank"
					alt="docs"
					rel="nofollow noopener noreferrer"
				>
					<Icon :name="ExternalIcon" :size="16" />
					docs
				</a>
			</div>
		</div>

		<div class="components-list">
			<CardCodeExample title="Circle">
				<template #description>
					Progress can be a circle. It can be
					<n-text code>default</n-text>
					,
					<n-text code>info</n-text>
					,
					<n-text code>success</n-text>
					,
					<n-text code>warning</n-text>
					or
					<n-text code>error</n-text>
					status.
				</template>
				<n-space vertical>
					<n-space>
						<n-progress type="circle" :percentage="percentage" />
						<n-progress type="circle" status="info" :percentage="percentage" />
						<n-progress type="circle" status="success" :percentage="percentage" />
						<n-progress type="circle" status="warning" :percentage="percentage" />
						<n-progress type="circle" status="error" :percentage="percentage" />
					</n-space>
					<n-space>
						<n-button @click="minus">Minus 10%</n-button>
						<n-button @click="add">Add 10%</n-button>
					</n-space>
				</n-space>
				<template #code="{ html, js }">
					{{ html(`
					<n-space vertical>
						<n-space>
							<n-progress type="circle" :percentage="percentage" />
							<n-progress type="circle" status="info" :percentage="percentage" />
							<n-progress type="circle" status="success" :percentage="percentage" />
							<n-progress type="circle" status="warning" :percentage="percentage" />
							<n-progress type="circle" status="error" :percentage="percentage" />
						</n-space>
						<n-space>
							<n-button @click="minus">Minus 10%</n-button>
							<n-button @click="add">Add 10%</n-button>
						</n-space>
					</n-space>
					`) }}

					{{
						js(`
						const percentage = ref(0)

						const add = () => {
							percentage.value += 10
							if (percentage.value > 100) {
								percentage.value = 0
							}
						}

						const minus = () => {
							percentage.value -= 10
							if (percentage.value < 0) {
								percentage.value = 100
							}
						}
						`)
					}}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Line">
				<template #description>
					In fact, progress of line type don't need four different styles. However, since UI has designed it,
					I finally implemented them all. It also support
					<n-text code>default</n-text>
					,
					<n-text code>info</n-text>
					,
					<n-text code>success</n-text>
					,
					<n-text code>warning</n-text>
					or
					<n-text code>error</n-text>
					status.
				</template>
				<n-space vertical>
					<n-progress type="line" :percentage="percentage1" :show-indicator="false" />
					<n-progress type="line" :percentage="percentage1" />
					<n-progress type="line" :percentage="percentage1" :indicator-placement="'inside'" />
					<n-progress type="line" status="info" :percentage="percentage1" :show-indicator="false" />
					<n-progress type="line" status="info" :percentage="percentage1" />
					<n-progress type="line" status="info" :percentage="percentage1" :indicator-placement="'inside'" />
					<n-progress type="line" status="success" :percentage="percentage1" :show-indicator="false" />
					<n-progress type="line" status="success" :percentage="percentage1" />
					<n-progress
						type="line"
						status="success"
						:percentage="percentage1"
						:indicator-placement="'inside'"
					/>
					<n-progress type="line" status="warning" :percentage="percentage1" :show-indicator="false" />
					<n-progress type="line" status="warning" :percentage="percentage1" />
					<n-progress
						type="line"
						status="warning"
						:percentage="percentage1"
						:indicator-placement="'inside'"
					/>
					<n-progress type="line" status="error" :percentage="percentage1" :show-indicator="false" />
					<n-progress type="line" status="error" :percentage="percentage1" />
					<n-progress type="line" status="error" :percentage="percentage1" :indicator-placement="'inside'" />
					<n-space>
						<n-button @click="minus1">Minus 10%</n-button>
						<n-button @click="add1">Add 10%</n-button>
					</n-space>
				</n-space>
				<template #code="{ html, js }">
					{{ html(`
					<n-space vertical>
						<n-progress type="line" :percentage="percentage" :show-indicator="false" />
						<n-progress type="line" :percentage="percentage" />
						<n-progress type="line" :percentage="percentage" :indicator-placement="'inside'" />
						<n-progress type="line" status="info" :percentage="percentage" :show-indicator="false" />
						<n-progress type="line" status="info" :percentage="percentage" />
						<n-progress
							type="line"
							status="info"
							:percentage="percentage"
							:indicator-placement="'inside'"
						/>
						<n-progress type="line" status="success" :percentage="percentage" :show-indicator="false" />
						<n-progress type="line" status="success" :percentage="percentage" />
						<n-progress
							type="line"
							status="success"
							:percentage="percentage"
							:indicator-placement="'inside'"
						/>
						<n-progress type="line" status="warning" :percentage="percentage" :show-indicator="false" />
						<n-progress type="line" status="warning" :percentage="percentage" />
						<n-progress
							type="line"
							status="warning"
							:percentage="percentage"
							:indicator-placement="'inside'"
						/>
						<n-progress type="line" status="error" :percentage="percentage" :show-indicator="false" />
						<n-progress type="line" status="error" :percentage="percentage" />
						<n-progress
							type="line"
							status="error"
							:percentage="percentage"
							:indicator-placement="'inside'"
						/>
						<n-space>
							<n-button @click="minus">Minus 10%</n-button>
							<n-button @click="add">Add 10%</n-button>
						</n-space>
					</n-space>
					`) }}

					{{
						js(`
						const percentage = ref(0)

						const add = () => {
							percentage.value += 10
							if (percentage.value > 100) {
								percentage.value = 0
							}
						}

						const minus = () => {
							percentage.value -= 10
							if (percentage.value < 0) {
								percentage.value = 100
							}
						}
						`)
					}}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Multiple circle">
				<n-space vertical>
					<n-el>
						<n-progress
							type="multiple-circle"
							:stroke-width="6"
							:circle-gap="0.5"
							:percentage="[
								percentage,
								(percentage + 10) % 100,
								(percentage + 20) % 100,
								(percentage + 30) % 100
							]"
							:color="[
								'var(--info-color)',
								'var(--success-color)',
								'var(--warning-color)',
								'var(--error-color)'
							]"
							:rail-style="[
								{ stroke: 'var(--info-color)', opacity: 0.3 },
								{ stroke: 'var(--success-color)', opacity: 0.3 },
								{ stroke: 'var(--warning-color)', opacity: 0.3 },
								{ stroke: 'var(--error-color)', opacity: 0.3 }
							]"
						>
							<div style="text-align: center">Circle racing!</div>
						</n-progress>
					</n-el>
					<n-space>
						<n-button @click="minus">Minus 10%</n-button>
						<n-button @click="add">Add 10%</n-button>
					</n-space>
				</n-space>
				<template #code="{ html, js }">
					{{ html(`
					<n-space vertical>
						<n-el>
							<n-progress
								type="multiple-circle"
								:stroke-width="6"
								:circle-gap="0.5"
								:percentage="[
									percentage,
									(percentage + 10) % 100,
									(percentage + 20) % 100,
									(percentage + 30) % 100
								]"
								:color="[
									'var(--info-color)',
									'var(--success-color)',
									'var(--warning-color)',
									'var(--error-color)'
								]"
								:rail-style="[
									{ stroke: 'var(--info-color)', opacity: 0.3 },
									{ stroke: 'var(--success-color)', opacity: 0.3 },
									{ stroke: 'var(--warning-color)', opacity: 0.3 },
									{ stroke: 'var(--error-color)', opacity: 0.3 }
								]"
							>
								<div style="text-align: center">Circle racing!</div>
							</n-progress>
						</n-el>
						<n-space>
							<n-button @click="minus">Minus 10%</n-button>
							<n-button @click="add">Add 10%</n-button>
						</n-space>
					</n-space>
					`) }}

					{{
						js(`
						const percentage = ref(0)

						const add = () => {
							percentage.value += 10
							if (percentage.value > 100) {
								percentage.value = 0
							}
						}

						const minus = () => {
							percentage.value -= 10
							if (percentage.value < 0) {
								percentage.value = 100
							}
						}
						`)
					}}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Processing">
				<n-progress type="line" :percentage="60" :indicator-placement="'inside'" processing />
				<template #code="{ html }">
					{{ html(`
					<n-progress type="line" :percentage="60" :indicator-placement="'inside'" processing />
					`) }}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NSpace, NProgress, NButton, NEl, NText } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
import { ref } from "vue"

const percentage = ref(0)

const add = () => {
	percentage.value += 10
	if (percentage.value > 100) {
		percentage.value = 0
	}
}

const minus = () => {
	percentage.value -= 10
	if (percentage.value < 0) {
		percentage.value = 100
	}
}

const percentage1 = ref(0)
const add1 = () => {
	percentage1.value += 10
	if (percentage1.value > 100) {
		percentage1.value = 0
	}
}
const minus1 = () => {
	percentage1.value -= 10
	if (percentage1.value < 0) {
		percentage1.value = 100
	}
}
</script>
