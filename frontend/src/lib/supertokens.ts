/**
 * SuperTokens initialization for Board of One frontend.
 *
 * Configures SuperTokens Web SDK for:
 * - Session management (httpOnly cookies)
 * - ThirdParty OAuth (Google, LinkedIn, GitHub)
 * - EmailPassword authentication
 * - Passwordless (magic link) authentication
 */

import SuperTokens from "supertokens-web-js";
import Session from "supertokens-web-js/recipe/session";
import ThirdParty from "supertokens-web-js/recipe/thirdparty";
import EmailPassword from "supertokens-web-js/recipe/emailpassword";
import Passwordless from "supertokens-web-js/recipe/passwordless";
import { env } from '$env/dynamic/public';

let isInitialized = false;

/**
 * Initialize SuperTokens SDK.
 * Should be called once on app mount in +layout.svelte.
 */
export function initSuperTokens() {
    if (isInitialized) {
        return; // Already initialized
    }

    SuperTokens.init({
        appInfo: {
            apiDomain: env.PUBLIC_API_URL || "http://localhost:8000",
            apiBasePath: "/api/auth",
            appName: "Board of One",
        },
        recipeList: [
            Session.init(),
            ThirdParty.init(),
            EmailPassword.init(),
            Passwordless.init(),
        ],
    });

    isInitialized = true;
}
