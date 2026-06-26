import type { RouteRecordRaw } from "vue-router"
import type { FormType } from "@/components/auth/types.d"
import { Layout } from "@/types/theme"
import AuthPage from "@/views/Auth.vue"

export const authRoutes: RouteRecordRaw[] = [
	{
		path: "/login",
		name: "Login",
		component: AuthPage,
		props: { formType: "signin" as FormType },
		meta: {
			title: "Login",
			theme: { layout: Layout.Blank, boxed: { enabled: false }, padded: { enabled: false } },
			checkAuth: true,
			skipPin: true
		}
	},
	{
		path: "/sso-callback",
		name: "SSOCallback",
		component: AuthPage,
		props: { formType: "signin" as FormType },
		meta: {
			title: "SSO Login",
			theme: { layout: Layout.Blank, boxed: { enabled: false }, padded: { enabled: false } },
			checkAuth: true,
			skipPin: true
		}
	},
	/*
	{
		path: "/register",
		name: "Register",
		component: AuthPage,
		props: { formType: "signup" as FormType },
		meta: {
			title: "Register",
			theme: { layout: Layout.Blank, boxed: { enabled: false }, padded: { enabled: false } },
			checkAuth: true,
			skipPin: true
		}
	},
	*/
	{
		path: "/logout",
		name: "Logout",
		redirect: "/login"
	}
]
