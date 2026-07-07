<template>
	<div class="page flex flex-col gap-4">
		<n-button quaternary class="self-start" @click="goBack">
			<template #icon>
				<Icon :name="BackIcon" />
			</template>
			Back
		</n-button>

		<IocDetails v-if="iocId != null" :ioc-id :embedded="false" />
		<n-empty v-else description="Invalid IOC ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import { NButton, NEmpty } from "naive-ui"
import { computed } from "vue"
import { useRoute, useRouter } from "vue-router"
import IocDetails from "@/components/aiAnalyst/IocDetails.vue"
import Icon from "@/components/common/Icon.vue"

const route = useRoute()
const router = useRouter()

const BackIcon = "carbon:arrow-left"

const iocId = computed(() => {
	const id = Number(route.params.id)
	return Number.isFinite(id) ? id : null
})

function goBack() {
	if (window.history.length > 1) {
		router.back()
		return
	}

	router.push({ name: "AiAnalyst" })
}
</script>
