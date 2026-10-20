<template>
	<div class="w-full max-w-md space-y-8">
		<!-- Logo and Title -->
		<div class="text-center">
			<div v-if="logo" class="mb-6">
				<img class="mx-auto h-12 w-auto" :src="logo" :alt="`${title} Logo`" />
			</div>
			<h2 class="mb-2 text-4xl font-bold text-gray-900">{{ title || "CoPilot" }}</h2>
			<p class="text-lg text-gray-600">Access your security dashboard and reports</p>
		</div>
		<!-- Login Form -->
		<div class="mt-8 rounded-lg bg-white px-6 py-8 shadow-lg">
			<form class="space-y-6">
				<!-- v-if -->
				<div>
					<label for="username" class="mb-2 block text-sm font-medium text-gray-700">Username</label>
					<input
						id="username"
						type="text"
						disabled
						autocomplete="username"
						class="block w-full rounded-md border border-gray-300 px-3 py-3 text-base placeholder-gray-400 shadow-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
						placeholder="Enter your username"
					/>
				</div>
				<div>
					<label for="password" class="mb-2 block text-sm font-medium text-gray-700">Password</label>
					<input
						id="password"
						type="password"
						disabled
						autocomplete="current-password"
						class="block w-full rounded-md border border-gray-300 px-3 py-3 text-base placeholder-gray-400 shadow-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
						placeholder="Enter your password"
					/>
				</div>
				<div>
					<!-- Shown as the portal shows it, enabled: a faded preview would misstate the color. -->
					<button
						type="button"
						tabindex="-1"
						data-testid="portal-preview-sign-in"
						class="group relative flex w-full cursor-default justify-center rounded-md border border-transparent px-4 py-3 text-base font-medium focus:outline-none"
						:style="themedButton"
					>
						<span>Sign in</span>
					</button>
				</div>
			</form>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed } from "vue"
import { loginPrimary, PORTAL_DEFAULT_PRIMARY } from "./brandTheme"

const { title, logo, brandColor, themed } = defineProps<{
	title?: string | null
	logo?: string | null
	brandColor?: string | null
	/** The portal takes the brand color as its primary (#1278). */
	themed?: boolean | null
}>()

// The portal's own default primary when it is not themed, so the preview shows what customers see.
const themedButton = computed(() => {
	const palette = loginPrimary(brandColor, themed) ?? PORTAL_DEFAULT_PRIMARY
	return { backgroundColor: palette.primary, color: palette.onPrimary }
})
</script>
