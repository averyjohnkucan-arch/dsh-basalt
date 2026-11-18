Current protocol: one selected configuration per model, measured at10% counting and90% prose,1024output tokens,final512timed. RESULTS.md supersedes older tuning status notes.

Harness scripts are exact host-specific records and reference the original scratch tree, model assets and dependencies documented in the parent benchmark directory. Do not launch them blindly on another machine. They do not ship weights or portable model manifests.

GPU runs are complete. The final recovery wrapper monitors pressure and stops only its owned scope; no ManagedOOMPreference=avoid is used. The selected model controls are unchanged by the12GiB non-model allowance.
