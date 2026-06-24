import { createRouter, createWebHistory } from "vue-router"
import { authCheck } from "@/utils/auth"
import { routes } from "./routes"

const router = createRouter({
	history: createWebHistory(import.meta.env.BASE_URL),
	routes
})

router.beforeEach(route => {
	return authCheck(route)
})

export default router
