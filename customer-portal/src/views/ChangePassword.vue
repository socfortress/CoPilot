<template>
	<main class="bg-body flex min-h-svh items-center justify-center p-4 sm:p-8" data-testid="change-password-page">
		<section
			class="bg-default border-default flex w-full max-w-120 flex-col gap-6 rounded-lg border p-6 sm:p-8"
			aria-labelledby="change-password-title"
		>
			<header class="flex flex-col gap-3">
				<Logo max-height="32px" class="justify-start!" />
				<div class="flex flex-col gap-1.5">
					<span class="text-tertiary font-mono text-[10px] tracking-[0.14em] uppercase">
						{{ $t("auth.forcedChange.eyebrow") }}
					</span>
					<h1 id="change-password-title" class="text-2xl leading-tight font-semibold">
						{{ $t("auth.forcedChange.title") }}
					</h1>
					<p class="text-secondary text-sm">
						{{ $t("auth.forcedChange.intro") }}
						<i18n-t v-if="userName" keypath="auth.forcedChange.chooseFor" scope="global">
							<template #username>
								<span class="text-default font-mono">{{ userName }}</span>
							</template>
						</i18n-t>
					</p>
				</div>
			</header>

			<ChangePasswordForm
				v-model:loading="loading"
				:current-label="$t('auth.forcedChange.currentLabel')"
				:current-placeholder="$t('auth.forcedChange.currentPlaceholder')"
				:submit-label="$t('auth.forcedChange.submit')"
				:cancel-label="$t('auth.forcedChange.signOut')"
				@cancel="signOut()"
				@success="continueToPortal()"
			/>
		</section>
	</main>
</template>

<script setup lang="ts">
import { ref } from "vue"
import { useRoute, useRouter } from "vue-router"
import Logo from "@/app-layouts/common/Logo.vue"
import ChangePasswordForm from "@/components/auth/ChangePasswordForm.vue"
import { useAuthStore } from "@/stores/auth"
import { getSafeRedirect } from "@/utils/auth"

// A password an admin chose (a temporary one emailed, a reset, a new account) must be
// replaced before the portal opens (#1277). The router holds the user here, and the API
// answers nothing else until the change.
const authStore = useAuthStore()
const route = useRoute()
const router = useRouter()
const loading = ref(false)
const userName = authStore.userName

function signOut() {
	router.replace({ name: "Logout" })
}

function continueToPortal() {
	authStore.setPasswordChangeRequired(false)
	router.replace(getSafeRedirect(route.query.redirect))
}
</script>
