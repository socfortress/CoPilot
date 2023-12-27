<template>
	<div class="customer-provision-wizard">
		<div class="wrapper flex flex-col">
			<div class="grow">
				<n-scrollbar x-scrollable trigger="none">
					<div class="p-7 pt-4">
						<n-steps :current="current" size="small" :status="currentStatus">
							<n-step title="Provisioning" />
							<n-step title="Graylog" />
							<n-step title="Subscription" />
							<n-step title="Wazuh Worker">
								<template #icon>
									<Icon :name="SkipIcon" v-if="!isWazuhEnabled"></Icon>
								</template>
							</n-step>
						</n-steps>
					</div>
				</n-scrollbar>

				<div class="form-container">
					{{ current }}

					<Transition :name="`slide-form-${slideFormDirection}`">
						<div v-if="current === 1">
							<n-button @click="next()">next</n-button>
						</div>
						<div v-else-if="current === 2">
							<n-button @click="prev()">prev</n-button>
							<n-button @click="next()">next</n-button>
						</div>
						<div v-else-if="current === 3">
							<n-button @click="prev()">prev</n-button>
							<n-button @click="next()" v-if="isWazuhEnabled">next</n-button>
							<n-button type="primary" @click="submit()" v-else>submit</n-button>
						</div>
						<div v-else-if="current === 4">
							<n-button @click="prev()">prev</n-button>
							<n-button type="primary" @click="submit()">submit</n-button>
						</div>
					</Transition>
				</div>
			</div>

			<slot name="additionalActions"></slot>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, ref, toRefs } from "vue"
import { NSteps, NStep, useMessage, NScrollbar, NButton, type StepsProps } from "naive-ui"
import type { CustomerMeta } from "@/types/customers.d"
import Icon from "@/components/common/Icon.vue"

const emit = defineEmits<{
	(e: "update:loading", value: boolean): void
	(e: "submitted", value: CustomerMeta): void
	(
		e: "mounted",
		value: {
			reset: () => void
		}
	): void
}>()

const props = defineProps<{
	customerCode: string
	customerName: string
}>()
const { customerCode, customerName } = toRefs(props)

const SkipIcon = "carbon:subtract"

const loading = ref(false)
const message = useMessage()
const current = ref<number>(1)
const currentStatus = ref<StepsProps["status"]>("process")

const isWazuhEnabled = computed(() => false)
const slideFormDirection = ref<"right" | "left">("right")

function next() {
	currentStatus.value = "process"
	slideFormDirection.value = "right"
	current.value++
}

function prev() {
	currentStatus.value = "process"
	slideFormDirection.value = "left"
	current.value--
}

function submit() {
	currentStatus.value = "finish"
}
</script>

<style lang="scss" scoped>
.customer-provision-wizard {
	.wrapper {
		min-height: 400px;
	}
}

.slide-form-right-enter-active,
.slide-form-right-leave-active,
.slide-form-left-enter-active,
.slide-form-left-leave-active {
	transition: all 0.2s ease-out;
	position: absolute;
}

.slide-form-left-enter-from {
	transform: translateX(-100%);
}

.slide-form-left-leave-to {
	transform: translateX(100%);
}

.slide-form-right-enter-from {
	transform: translateX(100%);
}

.slide-form-right-leave-to {
	transform: translateX(-100%);
}
</style>
