import { supportsProjection } from "./projection.js";
export function thinkingInfo(profile) {
  const deepseek = profile.model.architecture === "deepseek41";
  if (deepseek)
    return {
      defaultEffort: profile.defaultEffort ?? "high",
      efforts: [
        { id: "off", name: "Off", description: "Disable thinking" },
        { id: "low", name: "Low" },
        { id: "high", name: "High", description: "Native DeepSeek 75/100" },
        { id: "max", name: "Max", description: "Native DeepSeek 100/100" },
      ],
    };
  return {
    defaultEffort: "medium",
    efforts: [
      { id: "off", name: "Off", description: "Disable thinking" },
      { id: "low", name: "Low" },
      {
        id: "medium",
        name: "Medium",
        description: "Native default; no added effort instruction",
      },
      { id: "xhigh", name: "Xhigh" },
      ...(supportsProjection(profile)
        ? [
            {
              id: "uncensored",
              name: "Uncensored",
              description:
                "Medium with the Flash Next refusal-direction projection",
            },
          ]
        : []),
    ],
  };
}
export function thinkingPayload(
  profile,
  effort = thinkingInfo(profile).defaultEffort,
) {
  const deepseek = profile.model.architecture === "deepseek41";
  if (effort === "none") effort = "off";
  if (deepseek && effort === "xhigh") effort = "max";
  if (!deepseek && effort === "high") effort = "xhigh";
  if (!thinkingInfo(profile).efforts.some((x) => x.id === effort))
    throw Error("Unsupported Basalt reasoning effort: " + effort);
  const payload =
    effort === "off"
      ? {
          reasoning_effort: "none",
          enable_thinking: false,
          chat_template_kwargs: { enable_thinking: false },
        }
      : {
          reasoning_effort: effort === "uncensored" ? "medium" : effort,
          enable_thinking: true,
        };
  if (supportsProjection(profile))
    payload.experimental_speed_projection = effort === "uncensored";
  return payload;
}
