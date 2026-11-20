// Test-only entrypoint. Never deployed by wrangler.toml.
export { Watchdog } from "./worker.mjs";
export default {async fetch(request,env){const stub=env.WATCHDOG.get(env.WATCHDOG.idFromName("runtime-test"));return stub.fetch("https://watchdog.internal/tick",{method:"POST"});}};
