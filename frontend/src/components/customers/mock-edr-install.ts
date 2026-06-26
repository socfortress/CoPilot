import type { EDRInstallCommands } from "@/types/customers"

const MOCK_REPO_URL = "https://artifacts.example.local"
const MOCK_REPO_USERNAME = "socfortress"
const MOCK_REPO_PASSWORD = "changeme"
const MOCK_WINDOWS_INSTALLER = "WazuhAgentSetup.exe"
const MOCK_LINUX_INSTALLER = "Client_EDR_install.bash"
const MOCK_MACOS_INSTALLER = "macOS_kickstart.sh"
const MOCK_WAZUH_DOMAIN = "wazuh-manager.example.local"
const MOCK_REGISTRATION_PASSWORD = "registration-secret"
const MOCK_REGISTRATION_PORT = "1515"
const MOCK_LOGS_PORT = "1514"

export function buildMockEdrInstallCommands(customerCode: string): EDRInstallCommands {
	const windowsCustomerCode = `Windows_${customerCode}`
	const linuxCustomerCode = `Linux_${customerCode}`

	return {
		windows: [
			`$user = '${MOCK_REPO_USERNAME}'; $pass = '${MOCK_REPO_PASSWORD}';`,
			'$pair = "$($user):$($pass)";',
			"$encodedCreds = [System.Convert]::ToBase64String([System.Text.Encoding]::ASCII.GetBytes($pair));",
			'$basicAuthValue = "Basic $encodedCreds";',
			"$Headers = @{ Authorization = $basicAuthValue };",
			`Invoke-RestMethod -Uri '${MOCK_REPO_URL}/repository/${MOCK_REPO_USERNAME}/prod/${MOCK_WINDOWS_INSTALLER}'`,
			`-Headers $Headers -OutFile "$env:TMP\\${MOCK_WINDOWS_INSTALLER}";`,
			`Start-Process -FilePath "$env:TMP\\${MOCK_WINDOWS_INSTALLER}"`,
			`-ArgumentList '/q WAZUHMANAGER="${MOCK_WAZUH_DOMAIN}" WAZUHPASSWORD="${MOCK_REGISTRATION_PASSWORD}"`,
			`CUSTOMERCODE="${windowsCustomerCode}" WAZUHREGISTRATIONPORT="${MOCK_REGISTRATION_PORT}"`,
			`WAZUHMANAGERPORT="${MOCK_LOGS_PORT}"';`
		].join(" "),
		linux: [
			"if command -v apt >/dev/null 2>&1; then apt update && apt install -y sudo dos2unix;",
			"elif command -v yum >/dev/null 2>&1; then sudo yum install -y dos2unix;",
			'else echo "Error: Neither apt nor yum package manager found."; exit 1; fi;',
			`curl -u ${MOCK_REPO_USERNAME}:${MOCK_REPO_PASSWORD} -so ~/${MOCK_LINUX_INSTALLER}`,
			`${MOCK_REPO_URL}/repository/${MOCK_REPO_USERNAME}/installer/${MOCK_LINUX_INSTALLER} &&`,
			`dos2unix ~/${MOCK_LINUX_INSTALLER} &&`,
			`CLIENT_USER=${MOCK_REPO_USERNAME} CLIENT_PASS=${MOCK_REPO_PASSWORD} bash ~/${MOCK_LINUX_INSTALLER}`,
			`-i ${MOCK_WAZUH_DOMAIN} ${MOCK_LOGS_PORT} ${MOCK_REGISTRATION_PORT} ${MOCK_REGISTRATION_PASSWORD} ${linuxCustomerCode}`
		].join(" "),
		macos: [
			`curl -fsSL -u '${MOCK_REPO_USERNAME}:${MOCK_REPO_PASSWORD}'`,
			`'${MOCK_REPO_URL}/repository/${MOCK_REPO_USERNAME}/installer/${MOCK_MACOS_INSTALLER}'`,
			"| sudo bash -s -- --no-stagger"
		].join(" ")
	}
}

export const MOCK_EDR_INSTALL_COMMANDS = buildMockEdrInstallCommands("ACME")
