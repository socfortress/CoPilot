<template>
	<div class="w-full max-w-md space-y-8">
		<!-- Logo and Title -->
		<div class="text-center">
			<div class="mb-6">
				<img class="mx-auto h-12 w-auto" :src="logo || '/logo.svg'" alt="SOCFortress Logo" />
			</div>
			<h2 class="mb-2 text-4xl font-bold text-gray-900">{{ title || "SOCFortress Customer Portal" }}</h2>
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
					<button
						type="submit"
						disabled
						class="group relative flex w-full justify-center rounded-md border border-transparent bg-indigo-600 px-4 py-3 text-base font-medium text-white transition-colors duration-200 hover:bg-indigo-700 focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
					>
						<span>Sign in</span>
					</button>
				</div>
			</form>
		</div>
	</div>
</template>

<script setup lang="ts">
const { title, logo } = defineProps<{ title?: string | null; logo?: string | null }>()
</script>
