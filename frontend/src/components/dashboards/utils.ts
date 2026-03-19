export function getDashboardIcon(icon: string) {
	switch (icon) {
		case "cpu":
		case "memory":
			return "carbon:chip"
		case "network":
			return "carbon:load-balancer-network"
		case "storage":
			return "carbon:vmdk-disk"
		case "security":
			return "carbon:security"
		case "performance":
			return "ph:gauge"
		default:
			return "carbon:dashboard"
	}
}
