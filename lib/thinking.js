export function thinkingInfo(profile) {
  const deepseek = profile.model.architecture === "deepseek41";
  return {
    defaultEffort: deepseek ? "high" : "medium",
    efforts: [
      { id: "off", name: "Off", description: "Disable thinking" },
      { id: "low", name: "Low" },
      ...(deepseek
        ? []
        : [
            {
              id: "medium",
              name: "Medium",
              description:
                "No effort instruction added by the Basalt Qwen template",
            },
          ]),
      {
        id: "high",
        name: "High",
        description: deepseek
          ? "Native DeepSeek 75/100"
          : "Basalt xhigh effort instruction",
      },
      ...(deepseek
        ? [{ id: "max", name: "Max", description: "Native DeepSeek 100/100" }]
        : []),
    ],
  };
}
export function thinkingPayload(
  profile,
  effort = thinkingInfo(profile).defaultEffort,
) {
  if (effort === "none") effort = "off";
  if (effort === "xhigh")
    effort = profile.model.architecture === "deepseek41" ? "max" : "high";
  if (!thinkingInfo(profile).efforts.some((x) => x.id === effort))
    throw new Error("Unsupported Basalt reasoning effort: " + effort);
  return effort === "off"
    ? {
        reasoning_effort: "none",
        enable_thinking: false,
        chat_template_kwargs: { enable_thinking: false },
      }
    : { reasoning_effort: effort, enable_thinking: true };
}
