<template>
	<n-spin :show="loading" content-class=" grow flex flex-col" class="flex flex-col overflow-hidden">
		<div v-if="license" class="flex flex-col gap-4">
			<KVCard v-if="!hideKey">
				<template #key>
					<span class="flex gap-3 items-center">
						<Icon :name="KeyIcon" :size="14"></Icon>
						<span>Key</span>
					</span>
				</template>
				<template #value>
					{{ license.key }}
				</template>
			</KVCard>
			<KVCard v-if="!hideFeatures">
				<template #key>
					<span class="flex gap-3 items-center">
						<Icon :name="FeaturesIcon" :size="14"></Icon>
						<span>Features</span>
					</span>
				</template>
				<template #value>
					<div v-if="features.length" class="grid gap-2 grid-auto-fit-200">
						<KVCard v-for="feature of features" :key="feature">
							<template #value>
								<span class="flex gap-3 items-center">
									<Icon :name="CheckIcon" :size="14" class="text-primary-color"></Icon>
									<span>{{ feature }}</span>
								</span>
							</template>
						</KVCard>
					</div>
					<template v-else>No feature enabled</template>
				</template>
			</KVCard>
			<KVCard>
				<template #key>
					<span class="flex gap-3 items-center">
						<Icon :name="ExpiresIcon" :size="14"></Icon>
						<span>Expires</span>
					</span>
				</template>
				<template #value>
					{{ expiresText }}
					<span class="text-secondary-color">({{ periodText }})</span>
				</template>
			</KVCard>
			<KVCard>
				<template #key>
					<span class="flex gap-3 items-center">
						<Icon :name="CustomerIcon" :size="14"></Icon>
						<span>Customer</span>
					</span>
				</template>
				<template #value>
					<div class="flex flex-wrap gap-2">
						<Badge
							v-for="(value, key) of license.customer"
							:key="key"
							type="splitted"
							color="primary"
							fluid
						>
							<template #label>
								{{ sanitizeKey(key) }}
							</template>
							<template #value>
								<template v-if="key === 'created'">
									{{ formatDate(value, dFormats.datetime) }}
								</template>
								<template v-else>
									{{ value ?? "-" }}
								</template>
							</template>
						</Badge>
					</div>
				</template>
			</KVCard>
			<KVCard v-if="dockerCompose">
				<template #key>
					<span class="flex gap-3 items-center">
						<Icon :name="ConfigIcon" :size="14"></Icon>
						<span>Docker Configuration</span>
					</span>
				</template>
				<template #value>
					<Suspense>
						<Markdown :source="dockerCompose" code-bg-transparent />
					</Suspense>
				</template>
			</KVCard>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { License, LicenseFeatures } from "@/types/license.d"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import Icon from "@/components/common/Icon.vue"
import KVCard from "@/components/common/KVCard.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"
import _startCase from "lodash/startCase"
import { NSpin, useMessage } from "naive-ui"
import { computed, defineAsyncComponent, onBeforeMount, onMounted, ref, toRefs } from "vue"

const props = defineProps<{
	licenseData?: License
	featuresData?: LicenseFeatures[]
	hideKey?: boolean
	hideFeatures?: boolean
}>()

const emit = defineEmits<{
	(e: "licenseLoaded", value: License): void
	(
		e: "mounted",
		value: {
			reload: () => void
		}
	): void
}>()

const Markdown = defineAsyncComponent(() => import("@/components/common/Markdown.vue"))

const { licenseData, featuresData, hideKey, hideFeatures } = toRefs(props)

const KeyIcon = "ph:key"
const ExpiresIcon = "ph:calendar-blank"
const CustomerIcon = "carbon:user"
const CheckIcon = "carbon:checkmark-outline"
const FeaturesIcon = "material-symbols:checklist"
const ConfigIcon = "carbon:settings"

const message = useMessage()
const loadingLicense = ref(false)
const loadingFeatures = ref(false)
const loadingDockerCompose = ref(false)
const dFormats = useSettingsStore().dateFormat

const licenseLoaded = ref<License | null>(null)
const featuresLoaded = ref<LicenseFeatures[]>([])
const dockerCompose = ref<string | null>(null)
const license = computed(() => licenseLoaded.value || licenseData?.value || null)
const features = computed(() => featuresLoaded.value || featuresData?.value || [])
const expiresText = computed(() => (license.value ? formatDate(license.value.expires, dFormats.datetime) : ""))
const periodText = computed(() =>
	license.value ? `${license.value.period} Day${license.value.period === 1 ? "" : "s"}` : ""
)

const loading = computed(() => loadingLicense.value || loadingFeatures.value || loadingDockerCompose.value)

function getLicense() {
	loadingLicense.value = true

	Api.license
		.verifyLicense()
		.then(res => {
			if (res.data.success) {
				licenseLoaded.value = res.data?.license
				emit("licenseLoaded", licenseLoaded.value)
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			if (err.response.status !== 404) {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			}
		})
		.finally(() => {
			loadingLicense.value = false
		})
}

function getLicenseFeatures() {
	loadingFeatures.value = true

	Api.license
		.getLicenseFeatures()
		.then(res => {
			if (res.data.success) {
				featuresLoaded.value = res.data?.features
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			if (err.response.status !== 404) {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			}
		})
		.finally(() => {
			loadingFeatures.value = false
		})
}

function retrieveDockerCompose() {
	loadingDockerCompose.value = true

	Api.license
		.retrieveDockerCompose()
		.then(res => {
			if (res.data.success) {
				dockerCompose.value = res.data?.docker_compose
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			if (err.response.status !== 404) {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			}
		})
		.finally(() => {
			loadingDockerCompose.value = false
		})
}

function load() {
	if (!license.value) {
		getLicense()
	}
	if (!hideFeatures.value && !features.value.length) {
		getLicenseFeatures()
	}

	retrieveDockerCompose()
}

function sanitizeKey(text: string) {
	return _startCase(text).toLowerCase()
}

onBeforeMount(() => {
	load()
})

onMounted(() => {
	emit("mounted", {
		reload: load
	})
})
</script>
