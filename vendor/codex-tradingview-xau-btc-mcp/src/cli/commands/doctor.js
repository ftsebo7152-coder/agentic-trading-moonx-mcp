import { register } from "../router.js";
import { runDoctor } from "../../core/doctor.js";

register("doctor", {
  description: "Run a full Codex + TradingView Desktop Windows diagnostic",
  options: {
    host: { type: "string", description: "CDP host, default TRADINGVIEW_CDP_HOST or 127.0.0.1" },
    port: { type: "string", description: "CDP port, default TRADINGVIEW_CDP_PORT or 9222" },
  },
  handler: async ({ host, port }) => runDoctor({ host, port: port ? Number(port) : undefined }),
});
