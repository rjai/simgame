class GovernmentAgent:
    pass

class Agent:
    name = None

    def __init__(self, name):
        self.name = name

    def plan(self, reward, world):
        return [] # List of actions: buy/sell/create

class Action:
    pass

class CreateAction(Action):
    def __init__(self, resource, qty):
        pass

# negative qty is selling for agent
class TransactAction(Action):
    def __init__(self, resource, qty, price):
        pass

class Resource:
    initializationCost = (0, 0) # Number of turns, amount of money
    buildCost = (0, 0) # as above
    sourceResources = {} # Jewellery: 1 = {'gold': 3}
    name = None

    def __init__(self, name, initializationCost, buildCost, sourceResources):
        self.name = name
        self.initializationCost = initializationCost
        self.buildCost = buildCost
        self.sourceResources = sourceResources

class ResourceGraph:
    resourceArray = []
    def __init__(self, resourceConfigFile):
        pass

    def resourceArray(self):
        return self.resourceArray

class Market:
    {}

class World:
    agentInfo = {}
    agents = []
    market = None
    resourceGraph = None

    def __init__(self, worldInitializationConfig, agents, resourceGraph):
        self.agents = agents
        self.agentInfo = {}
        for agent in agents:
            self.agentInfo[agent]['money'] = worldInitializationConfig['agentMoneyGenerator'](agent)
            self.agentInfo[agent]['resources'] = worldInitializationConfig['agentResourceGenerator'](agent, resourceGraph)
            self.agentInfo[agent]['capabilities'] = set()
        self.resourceGraph = resourceGraph

class GameConfig:
    pass

class Simulator:
    world = None
    agents = []
    resourceGraph = None
    turn = 0

    def __init__(self, worldInitializationConfig, resourceGraph):
        self.resourceGraph = resourceGraph
        self.agents = [Agent(x) for x in range(worldInitializationConfig['numAgents'])]
        self.world = World(worldInitializationConfig, self.agents, resourceGraph)

    def runSimulationStep(self):
        completePlan = {}
        for agent in self.agents:
            agentPlan = agent.plan(self.agentRewards[agent], self.world.agentInfo[agent], self.world.market) # TODO: Define agentRewards
            completePlan[agent] = agentPlan

        newWorld = self.generateNewWorld(completePlan)
        self.world = newWorld
        self.turn += 1

    def runSimulation(self, numTurns):
        for _ in numTurns:
            self.runSimulationStep()