import { useRouter } from "vue-router"

export function useGoto() {
	const router = useRouter()

	function gotoCustomer(code?: string | number | { [key: string]: any }) {
		if (code) {
			router.push({ name: "Customers", query: { code: code.toString() } })
		} else {
			router.push({ name: "Customers" })
		}
	}

	return {
		gotoCustomer
	}
}
