<template>
	<div class="overview-section">
		<div class="property-group">
			<KVCard v-for="item of propsSanitized" :key="item.key">
				<template #key>{{ item.key }}</template>
				<template #value>
					<template v-if="item.key === 'customer_code'">
						<code
							class="cursor-pointer text-primary-color"
							@click="gotoCustomer(item.val)"
							v-if="item.val && item.val !== '-'"
						>
							{{ item.val }}
							<Icon :name="LinkIcon" :size="13" class="relative top-0.5" />
						</code>
						<span v-else>-</span>
					</template>
					<template v-else>
						{{ item.val ?? "-" }}
					</template>
				</template>
			</KVCard>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, toRefs } from "vue"
import dayjs from "@/utils/dayjs"
import { type Agent } from "@/types/agents.d"
import { useSettingsStore } from "@/stores/settings"
import KVCard from "@/components/common/KVCard.vue"
import Icon from "@/components/common/Icon.vue"
import { useRouter } from "vue-router"

const props = defineProps<{
	agent: Agent
}>()
const { agent } = toRefs(props)

const LinkIcon = "carbon:launch"
const router = useRouter()
const dFormats = useSettingsStore().dateFormat

const propsSanitized = computed(() => {
	const obj = []
	for (const key in agent.value) {
		if (["wazuh_last_seen", "velociraptor_last_seen"].includes(key)) {
			// @ts-ignore
			obj.push({ key, val: formatDate(agent.value[key]) || "-" })
		} else {
			// @ts-ignore
			obj.push({ key, val: agent.value[key] || "-" })
		}
	}

	return obj
})

const formatDate = (date: string) => {
	const datejs = dayjs(date)
	if (!datejs.isValid()) return date

	return datejs.format(dFormats.datetime)
}

function gotoCustomer(code: string | number) {
	router.push({ name: "Customers", query: { code } })
}
</script>

<style lang="scss" scoped>
.overview-section {
	container-type: inline-size;

	.property-group {
		width: 100%;
		display: grid;
		@apply gap-2;
		grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
		grid-auto-flow: row dense;
	}

	@container (max-width: 500px) {
		.property-group {
			grid-template-columns: repeat(auto-fit, 100%);
		}
	}
}
</style>
