from ray.tune.registry import register_env
import ray
import ray.tune as tune

from agent import WorldEnv, ResourceGraph, gameConfig

if __name__ == "__main__":  

    register_env(
        "VillageEconomics", 
        lambda _: WorldEnv(gameConfig, ResourceGraph()))

    sim = WorldEnv(gameConfig, ResourceGraph())

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
            "num_workers": 1,
            "num_cpus_for_driver": 1,
            "num_cpus_per_worker": 1,
            "lr": 5e-3,
            "model": {"fcnet_hiddens": [8, 8]},
            "multiagent": {
                "policies": {
                    'agent-' + str(i): (None, sim.observation_space, sim.action_space, {})
                        for i in range(sim.num_agents)
                },
                "policy_mapping_fn": lambda aid: "agent-"+str(aid) if "agent-" not in str(aid) else str(aid),
            },
            "env": "VillageEconomics"
        }
    )
