<!-- filepath: /Users/taylor/Desktop/Repos/CoPilot/frontend/src/components/common/AccessDenied.vue -->
<template>
	<div class="access-denied-container">
		<n-result
			status="403"
			title="Access Denied"
			:description="description || 'You do not have permission to view this page.'"
		>
			<template #footer>
				<n-space justify="center">
					<n-button type="primary" @click="goBack">
						<template #icon>
							<n-icon>
								<ArrowBackOutline />
							</n-icon>
						</template>
						Go Back
					</n-button>
					<n-button @click="goHome">
						<template #icon>
							<n-icon>
								<HomeOutline />
							</n-icon>
						</template>
						Go to Dashboard
					</n-button>
				</n-space>
			</template>
		</n-result>
	</div>
</template>

<script setup lang="ts">
// TODO: refactor
import { ArrowBackOutline, HomeOutline } from "@vicons/ionicons5"
import { useRouter } from "vue-router"

interface Props {
	description?: string
}

defineProps<Props>()

const router = useRouter()

function goBack() {
	router.back()
}

function goHome() {
	router.push("/")
}
</script>

<style scoped>
.access-denied-container {
	display: flex;
	align-items: center;
	justify-content: center;
	min-height: 60vh;
}
</style>
