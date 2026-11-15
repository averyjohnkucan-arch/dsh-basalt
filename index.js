import z from "@deepseek-ai/schemastery";
import { BasaltService } from "./lib/service.js";
import { BasaltAdapter } from "./lib/adapter.js";
import { attachScheduler } from "./lib/scheduler.js";
import { actionPath, handler } from "./lib/http.js";

export const inject = ["llm", "connection"];
export const Config = z.object({
  dataDir: z
    .string()
    .description("Private Basalt runtime, profiles and cache folder.")
    .default(""),
});
export async function apply(ctx, config) {
  let registration;
  const service = new BasaltService(config, () => {
    try {
      registration?.replace(["basalt"]);
    } catch (error) {
      if (error.code === "REGISTRATION_DISPOSED") registration = undefined;
      else throw error;
    }
  });
  await service.init();
  ctx.effect(() => () => service.dispose());
  ctx.effect(() => {
    const owned = ctx.llm.registerAdapter(
      ["basalt"],
      new BasaltAdapter(ctx, service),
    );
    registration = owned;
    return () => {
      registration = undefined;
      owned();
    };
  });
  ctx.effect(() =>
    ctx.connection.fetch.register({
      path: actionPath,
      methods: ["POST"],
      requestBody: "buffered",
      fetch: handler(service),
    }),
  );
  attachScheduler(ctx, service);
  // Activation only registers saved models. Runtime preparation and GPU loading are explicit operations.
}
