'use client';

import { useState } from 'react';

import { AgentSettingsFields } from '@/components/AgentSettingsForm';
import { Dropdown, DropdownOption } from '@/components/UI';
import { DEFAULT_AGENT_MODEL } from '@/constants';
import { useListAllDeployments } from '@/hooks';

type Props = {
  fields: AgentSettingsFields;
  nameError?: string;
  setFields: (fields: AgentSettingsFields) => void;
};

export const ConfigStep: React.FC<Props> = ({ fields, setFields }) => {
  const [selectedDeploymentValue, setSelectedDeploymentValue] = useState<string | undefined>(DEFAULT_AGENT_MODEL);
  const [selectedValue, setSelectedValue] = useState<string | undefined>(DEFAULT_AGENT_MODEL);
  const { data: deployments } = useListAllDeployments();

  // const selectedDeploymentModels = deployments?.find(
  //   ({ name }) => name === fields.deployment
  // )?.models;

  const filteredDeployments = deployments?.filter((dep)=> dep.is_available)
  
  const deploymentOptions: DropdownOption[] = filteredDeployments?.map((deployment) => ({ value: deployment.name, label: deployment.name })) || [];
  console.log(deploymentOptions);
  let modelOptions: DropdownOption[] = []
  
  function getModelOptions(deployment: string | undefined) {
    if (!deployment) return []
    modelOptions = filteredDeployments?.filter((dep) => dep.name === deployment)?.map(({ models }) => models.map((model) => ({ value: model, label: model }))).flat() || []
    return modelOptions ?? []
  }
  return (
    <div className="flex flex-col space-y-4">
      <Dropdown
        label="Deployment"
        options={deploymentOptions}
        value={selectedDeploymentValue}
        onChange={(deployment) => {
          setFields({ ...fields, deployment: deployment });
          setSelectedDeploymentValue(deployment);
        }}
      />
      
      <Dropdown
        label="Model"
        options={getModelOptions(selectedDeploymentValue)}
        value={selectedValue}
        onChange={(model) => {
          setFields({ ...fields, model: model });
          setSelectedValue(model);
        }}
      />
    </div>
  );
};
