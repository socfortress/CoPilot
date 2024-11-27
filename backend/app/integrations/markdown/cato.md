# [CATO NETWORKS](https://api.catonetworks.com/documentation/)

Cato Networks offers a comprehensive Secure Access Service Edge (SASE) platform that combines networking and security services into a single cloud-based solution. This integration allows you to ingest CATO NETWORK events into the SOCFortress SIEM stack.

# Overview of Cato API Keys

The **API Keys** page in the Cato Management Application allows you to generate keys for authenticating API clients or scripts. Cato supports two types of API permissions:

- **View permissions**: Perform read-only API calls to retrieve data from your account.
- **Edit permissions**: Perform write API calls to make changes to your account.

**Important**: After generating an API key, copy it immediately from the pop-up window. Once closed, the key cannot be retrieved.

**Note**: If you’re using the `eventsFeed` API to ingest event data, ensure that you enable integration with Cato events in the **Administration > Event Integrations** page.

## Managing API Keys

The **API Keys** page displays all keys associated with your account. You can generate new keys or revoke existing ones as needed. The **Name** assigned to an API key is solely for identification and isn’t used in the authentication process.

## Generating an API Key

To generate an API key:

1. In the navigation menu, click **Administration > API Management**.
2. On the **API Keys** tab, click **New**. The **Create API Key** panel will open.
3. Enter a **Key Name**.
4. Select the desired **API Permission** for this key.
5. (Optional) Set an **Expiration Date** for the API key. For keys with **Edit permissions**, it’s recommended to set an expiration date.
6. (Optional) For additional security, under **Allow access from IPs**, select **Specific IP list** and define the IP addresses permitted to use this API key. By default, the key is allowed for any IP address.
7. Click **Apply**. A pop-up window containing the new API key will appear.
8. Click the **Copy** icon and save the API key to a secure location. Once you close this window, the key cannot be accessed again.
9. Click **OK** to close the pop-up window.

For more detailed information, refer to **Cato Networks’ official documentation** on [Generating API Keys for the Cato API](https://support.catonetworks.com/hc/en-us/articles/4413280536081-Generating-API-Keys-for-the-Cato-API).

## Obtain Your Account ID from Cato Networks

1. **Log in** to your Cato Networks Editors Account.
2. **Record the Account ID** that appears in the Cato Networks URL to a temporary text file.
   - If you have multiple account IDs you wish to monitor, repeat this step for each.
   - For example, if your Account ID is `1234`, the URL should look like:
     `https://socfortress.catonetworks.com/#!/1234/topology`

3. Open the **Navigation Menu** and click **Administration > API Management**.
4. Enter the **Name** of the key and click **Apply**.
   - If the API key has been successfully added, a window will appear displaying the new API key.
5. Click the **Copy Icon** to copy your API key and ensure you **save it to a secure location**.
   - **Note**: Once you close the window, you can no longer access the value of the API key.
6. Click **OK** to close the API window.
7. On the **API Management** page, click the **Event Feed Enabled** toggle to enable your account to send events to the Cato API servers.
