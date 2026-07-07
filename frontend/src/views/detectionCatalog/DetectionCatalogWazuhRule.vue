<template>
	<div class="page flex flex-col gap-4">
		<n-button quaternary class="self-start" @click="goBack">
			<template #icon>
				<Icon :name="BackIcon" />
			</template>
			Back
		</n-button>

		<WazuhRuleDetail v-if="ruleId != null" :rule-id="ruleId" />
		<n-empty v-else description="Invalid Wazuh rule ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import { NButton, NEmpty } from "naive-ui"
import { computed } from "vue"
import { useRoute, useRouter } from "vue-router"
import WazuhRuleDetail from "@/components/detectionCatalog/WazuhRuleDetail.vue"
import Icon from "@/components/common/Icon.vue"

const route = useRoute()
const router = useRouter()

const BackIcon = "carbon:arrow-left"

const ruleId = computed(() => {
	const id = Number(route.params.id)
	return Number.isFinite(id) ? id : null
})

function goBack() {
	if (window.history.length > 1) {
		router.back()
		return
	}

	router.push({ name: "DetectionCatalog" })
}
</script>
