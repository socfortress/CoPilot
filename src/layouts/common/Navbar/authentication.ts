import { renderIcon } from "@/utils"
import { h } from "vue"

const AuthenticationIcon = "fluent:lock-closed-24-regular"

export default {
	label: "Authentication",
	key: "authentication",
	icon: renderIcon(AuthenticationIcon),
	children: [
		{
			label: () =>
				h(
					"a",
					{
						href: "/logout?step=signin"
					},
					"Log in"
				),
			key: "signin"
		},
		{
			label: () =>
				h(
					"a",
					{
						href: "/logout?step=signup"
					},
					"Sign up"
				),
			key: "signup"
		},
		{
			label: () =>
				h(
					"a",
					{
						href: "/logout?step=forgotpassword"
					},
					"Forgot password"
				),
			key: "forgotpassword"
		}
	]
}
