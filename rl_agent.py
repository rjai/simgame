from ray.tune.registry import register_env
import ray
import ray.tune as tune

from agent import Simulator, ResourceGraph

#ConfigStart
import random

def agentMoneyGenerator(agent):
    return random.randint(10,100)

def agentResourceGenerator(agent, resourceGraph):
    return {
        resource : random.randint(10,10000)
            for resource in resourceGraph.resourceArray()
    }

def agentAppetiteGenerator(agent, resourceGraph):
    return {
        resource: 1
            for resource in resourceGraph.resourceArray()
    }

gameConfig = {
    "numAgents": 10000,
    "money": agentMoneyGenerator,
    "resources": agentResourceGenerator,
    "appetite": agentAppetiteGenerator
}
#ConfigEnd


if __name__ == "__main__":  

    register_env(
        "VillageEconomics", 
        lambda: Simulator(gameConfig, ResourceGraph()))

    ray.init()
    tune.run(
        name= 'smart_eco',
        run_or_experiment= 'PG',
        stop= {
            "training_iteration": 100
        },
        checkpoint_freq= 20,
        config= {
            "log_level": "WARN",
            "num_workers": 3,
            "num_cpus_for_driver": 1,
            "num_cpus_per_worker": 1,
            "lr": 5e-3,
            "model": {"fcnet_hiddens": [8, 8]},
            "multiagent": {
                "policies": {
                    'agent-' + str(i): (None, sim.observation_space, sim.action_space, {})
                        for i in range(sim.num_agents)
                },
                "policy_mapping_fn": lambda aid: 'agent-' + str(aid),
            },
            "env": "IrrigationEnv"
        }
    )