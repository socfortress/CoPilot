<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Steps</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/steps"
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
			<CardCodeExample title="Basic">
				<n-space vertical>
					<n-space class="mb-4">
						<n-button-group>
							<n-button @click="prev">
								<template #icon>
									<Icon :name="ArrowBack" />
								</template>
							</n-button>
							<n-button @click="next">
								<template #icon>
									<Icon :name="ArrowForward" />
								</template>
							</n-button>
						</n-button-group>
						<n-radio-group v-model:value="currentStatus" size="medium" name="basic">
							<n-radio-button value="error">Error</n-radio-button>
							<n-radio-button value="process">Process</n-radio-button>
							<n-radio-button value="wait">Wait</n-radio-button>
							<n-radio-button value="finish">Finish</n-radio-button>
						</n-radio-group>
					</n-space>

					<n-steps :current="currentRef as number" :status="currentStatus">
						<n-step title="I Me Mine" description="All through the day, I me mine I me mine, I me mine" />
						<n-step
							title="Let It Be"
							description="When I find myself in times of trouble Mother Mary comes to me"
						/>
						<n-step title="Come Together" description="Here come old flat top He come grooving up slowly" />
						<n-step
							title="Something"
							description="Something in the way she moves Attracts me like no other lover"
						/>
					</n-steps>
				</n-space>
				<template #code="{ html, js }">
					{{ html(`
					<n-space vertical>
						<n-space class="mb-4">
							<n-button-group>
								<n-button @click="prev">
									<template #icon>
										<n-icon>
											<arrow-back />
										</n-icon>
									</template>
								</n-button>
								<n-button @click="next">
									<template #icon>
										<n-icon>
											<arrow-forward />
										</n-icon>
									</template>
								</n-button>
							</n-button-group>
							<n-radio-group v-model:value="currentStatus" size="medium" name="basic">
								<n-radio-button value="error">Error</n-radio-button>
								<n-radio-button value="process">Process</n-radio-button>
								<n-radio-button value="wait">Wait</n-radio-button>
								<n-radio-button value="finish">Finish</n-radio-button>
							</n-radio-group>
						</n-space>

						<n-steps :current="currentRef as number" :status="currentStatus">
							<n-step
								title="I Me Mine"
								description="All through the day, I me mine I me mine, I me mine"
							/>
							<n-step
								title="Let It Be"
								description="When I find myself in times of trouble Mother Mary comes to me"
							/>
							<n-step
								title="Come Together"
								description="Here come old flat top He come grooving up slowly"
							/>
							<n-step
								title="Something"
								description="Something in the way she moves Attracts me like no other lover"
							/>
						</n-steps>
					</n-space>
					`) }}

					{{
						js(`
						import { ArrowBack, ArrowForward } from "@vicons/ionicons5"
						import { ref } from "vue"

						const currentRef = ref\<\number | null\>\(1)
						const currentStatus = ref\<\StepsProps["status"]\>\("process")
						function next() {
							if (currentRef.value === null) currentRef.value = 1
							else if (currentRef.value >= 4) currentRef.value = null
							else currentRef.value++
						}
						function prev() {
							if (currentRef.value === 0) currentRef.value = null
							else if (currentRef.value === null) currentRef.value = 4
							else currentRef.value--
						}						
						`)
					}}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Vertical">
				<n-space vertical>
					<n-steps vertical :current="currentRef as number" :status="currentStatus">
						<n-step title="I Me Mine" description="All through the day, I me mine I me mine, I me mine" />
						<n-step
							title="Let It Be"
							description="When I find myself in times of trouble Mother Mary comes to me"
						/>
						<n-step title="Break" />
						<n-step title="Come Together" description="Here come old flat top He come grooving up slowly" />
						<n-step
							title="Something"
							description="Something in the way she moves Attracts me like no other lover"
						/>
					</n-steps>
					<n-space>
						<n-button-group>
							<n-button @click="prev">
								<template #icon>
									<Icon :name="ArrowBack" />
								</template>
							</n-button>
							<n-button @click="next">
								<template #icon>
									<Icon :name="ArrowForward" />
								</template>
							</n-button>
						</n-button-group>
						<n-radio-group v-model:value="currentStatus" size="medium" name="vertical">
							<n-radio-button value="error">Error</n-radio-button>
							<n-radio-button value="process">Process</n-radio-button>
							<n-radio-button value="wait">Wait</n-radio-button>
							<n-radio-button value="finish">Finish</n-radio-button>
						</n-radio-group>
					</n-space>
				</n-space>
				<template #code="{ html, js }">
					{{ html(`
					<n-space vertical>
						<n-steps vertical :current="current as number" :status="currentStatus">
							<n-step
								title="I Me Mine"
								description="All through the day, I me mine I me mine, I me mine"
							/>
							<n-step
								title="Let It Be"
								description="When I find myself in times of trouble Mother Mary comes to me"
							/>
							<n-step title="Break" />
							<n-step
								title="Come Together"
								description="Here come old flat top He come grooving up slowly"
							/>
							<n-step
								title="Something"
								description="Something in the way she moves Attracts me like no other lover"
							/>
						</n-steps>
						<n-space>
							<n-button-group>
								<n-button @click="prev">
									<template #icon>
										<n-icon>
											<arrow-back />
										</n-icon>
									</template>
								</n-button>
								<n-button @click="next">
									<template #icon>
										<n-icon>
											<arrow-forward />
										</n-icon>
									</template>
								</n-button>
							</n-button-group>
							<n-radio-group v-model:value="currentStatus" size="medium" name="vertical">
								<n-radio-button value="error">Error</n-radio-button>
								<n-radio-button value="process">Process</n-radio-button>
								<n-radio-button value="wait">Wait</n-radio-button>
								<n-radio-button value="finish">Finish</n-radio-button>
							</n-radio-group>
						</n-space>
					</n-space>
					`) }}

					{{
						js(`
						import { ArrowBack, ArrowForward } from "@vicons/ionicons5"
						import { ref } from "vue"

						const currentRef = ref\<\number | null\>\(1)
						const currentStatus = ref\<\StepsProps["status"]\>\("process")
						function next() {
							if (currentRef.value === null) currentRef.value = 1
							else if (currentRef.value >= 4) currentRef.value = null
							else currentRef.value++
						}
						function prev() {
							if (currentRef.value === 0) currentRef.value = null
							else if (currentRef.value === null) currentRef.value = 4
							else currentRef.value--
						}						
						`)
					}}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NSpace, NSteps, NStep, NButtonGroup, NRadioGroup, NRadioButton, NButton, type StepsProps } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
const ArrowBack = "ion:arrow-back"
const ArrowForward = "ion:arrow-forward"

import { ref } from "vue"

const currentRef = ref<number | null>(1)
const currentStatus = ref<StepsProps["status"]>("process")
function next() {
	if (currentRef.value === null) currentRef.value = 1
	else if (currentRef.value >= 4) currentRef.value = null
	else currentRef.value++
}
function prev() {
	if (currentRef.value === 0) currentRef.value = null
	else if (currentRef.value === null) currentRef.value = 4
	else currentRef.value--
}
</script>

<style lang="scss" scoped>
.components-list {
	grid-template-columns: none;
}
</style>
