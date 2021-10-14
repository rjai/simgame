from ray.tune.registry import register_env
import ray
import ray.tune as tune

from agent import WorldEnv, ResourceGraph, gameConfig

if __name__ == "__main__":  

    register_env(
        "VillageEconomics", 
        lambda _: WorldEnv(gameConfig, ResourceGraph()))

    sim = WorldEnv(gameConfig, ResourceGraph())

    ray.init(dashboard_port=40001, num_cpus=32, num_gpus=0, dashboard_host='0.0.0.0')
    tune.run(
        name= 'smart_eco',
        run_or_experiment= 'PG',
        stop= {
            "training_iteration": 100000
        },
        checkpoint_freq= 20,
        config= {
            "log_level": "WARN",
            "num_workers": 14,
            "num_cpus_for_driver": 1,
            "num_cpus_per_worker": 2,
            "lr": 5e-3,
            "model": {"fcnet_hiddens": [256, 256]},
            "multiagent": {
                "policies": {
                    "0": (None, sim.observation_space, sim.action_space, {})
                },
                "policy_mapping_fn": lambda aid: "0",
            },
            "env": "VillageEconomics"
        }
    )
