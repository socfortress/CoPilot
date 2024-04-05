<template>
	<n-spin :show="loading" content-class="min-h-48">
		<div class="license-details-box flex flex-col gap-7" :class="{ embedded }" v-if="license">
			<div class="section" v-if="!hideKey">
				<div class="label">
					<Icon :name="KeyIcon" :size="14"></Icon>
					Key
				</div>
				<div class="value">{{ license.key }}</div>
			</div>
			<div class="section" v-if="!hideFeatures">
				<div class="label">
					<Icon :name="FeaturesIcon" :size="14"></Icon>
					Features
				</div>
				<div class="value flex flex-wrap gap-2">
					<template v-if="features.length">
						<KVCard v-for="feature of features" :key="feature">
							<template #value>{{ feature }}</template>
						</KVCard>
					</template>
					<template v-else>No feature enabled</template>
				</div>
			</div>
			<div class="section">
				<div class="label">
					<Icon :name="ExpiresIcon" :size="14"></Icon>
					Expires
				</div>
				<div class="value">{{ expiresText }}</div>
			</div>
			<div class="section">
				<div class="label">
					<Icon :name="PeriodIcon" :size="14"></Icon>
					Period
				</div>
				<div class="value">{{ periodText }}</div>
			</div>
			<div class="section">
				<div class="label">
					<Icon :name="CustomerIcon" :size="14"></Icon>
					Customer
				</div>
				<div class="value grid gap-2 grid-auto-flow-200">
					<KVCard v-for="(value, key) of license.customer" :key="key">
						<template #key>{{ key }}</template>
						<template #value>
							<template v-if="key === 'Created'">
								{{ formatDate(value, dFormats.datetime) }}
							</template>
							<template v-else>{{ value ?? "-" }}</template>
						</template>
					</KVCard>
				</div>
			</div>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import { NSpin, useMessage } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import Api from "@/api"
import { onBeforeMount, onMounted, ref, toRefs, computed } from "vue"
import { LicenseFeatures, type License } from "@/types/license.d"
import { formatDate } from "@/utils"
import { useSettingsStore } from "@/stores/settings"
import KVCard from "@/components/common/KVCard.vue"

const emit = defineEmits<{
	(
		e: "mounted",
		value: {
			reload: () => void
		}
	): void
}>()

const props = defineProps<{
	licenseData?: License
	featuresData?: LicenseFeatures[]
	hideKey?: boolean
	hideFeatures?: boolean
	embedded?: boolean
}>()
const { licenseData, featuresData, hideKey, hideFeatures, embedded } = toRefs(props)

const KeyIcon = "ph:key"
const ExpiresIcon = "ph:calendar-blank"
const PeriodIcon = "majesticons:clock-line"
const CustomerIcon = "carbon:user"
const FeaturesIcon = "material-symbols:checklist"

const message = useMessage()
const loadingLicense = ref(false)
const loadingFeatures = ref(false)
const dFormats = useSettingsStore().dateFormat

const licenseLoaded = ref<License | null>(null)
const featuresLoaded = ref<LicenseFeatures[]>([])
const license = computed(() => licenseData?.value || licenseLoaded.value || null)
const features = computed(() => featuresData?.value || featuresLoaded.value || [])
const expiresText = computed(() => (license.value ? formatDate(license.value.expires, dFormats.datetime) : ""))
const periodText = computed(() =>
	license.value ? `${license.value.period} Day${license.value.period === 1 ? "" : "s"}` : ""
)

const loading = computed(() => loadingLicense.value || loadingFeatures.value)

function getLicense() {
	loadingLicense.value = true

	Api.license
		.verifyLicense()
		.then(res => {
			if (res.data.success) {
				licenseLoaded.value = res.data?.license
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

function load() {
	if (!license.value) {
		getLicense()
	}
	if (!hideFeatures.value && !features.value.length) {
		getLicenseFeatures()
	}
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

<style lang="scss" scoped>
.license-details-box {
	background-color: var(--bg-color);
	border-radius: var(--border-radius);

	&:not(.embedded) {
		padding: 14px 18px;
	}

	.section {
		display: flex;
		flex-direction: column;
		gap: 6px;
		.label {
			display: flex;
			align-items: center;
			gap: 10px;
			color: var(--fg-secondary-color);
			font-family: var(--font-family-mono);
			font-size: 14px;
		}

		.value {
			font-size: 16px;
			font-weight: bold;
		}
	}
}
</style>
