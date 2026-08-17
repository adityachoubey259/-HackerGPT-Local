import { Select } from "../ui/Form";
import { useModelStore } from "../../stores/modelStore";

export function ModelSelector() {
  const models = useModelStore((state) => state.models);
  const selectedProvider = useModelStore((state) => state.selectedProvider);
  const selectedModel = useModelStore((state) => state.selectedModel);
  const selectModel = useModelStore((state) => state.selectModel);
  const value = selectedProvider && selectedModel ? `${selectedProvider}/${selectedModel}` : "";
  return (
    <Select
      aria-label="Model"
      className="max-w-[16rem] text-technical text-xs"
      value={value}
      onChange={(event) => {
        const [provider, model] = event.target.value.split("/");
        if (provider && model) {
          selectModel(provider, model);
        }
      }}
    >
      <option value="">Select model</option>
      {models.map((model) => (
        <option key={model.id} value={`${model.provider}/${model.provider_model_id}`}>
          {model.name}
        </option>
      ))}
    </Select>
  );
}
