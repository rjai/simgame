"""
TODO
    - rewards
    - generation of new world
        - aggregation of actions (market)

"""

import collections

"""
    Modelling Actors in our simulation
        (Serves as a wrapper for the RI algo)
"""

class GovernmentAgent:
    pass

class Agent:
    name = None

    def __init__(self, name):
        self.name = name

    def plan(self, reward, world):
        return [] # List of actions: buy/sell/create


"""
    Modelling Agent's Actions 
"""

class Action:
    def __init__(self, agent, resource, qty):
        self.agent = agent
        self.resource = resource
        self.qty = qty

class CreateAction(Action):
    def __init__(self, agent, resource, qty):
        super(TransactAction, self).__init__(self, agent, resource, qty)

# negative qty is selling for agent
class TransactAction(Action):
    def __init__(self, agent, resource, qty, price):
        super(TransactAction, self).__init__(self, agent, resource, qty)
        self.price = price


"""
    Modelling the Environment
"""

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
    
    def __init__(self, resourceGraph):
        self.lastPrices = {resource : None for resource in resourceGraph.resourceArray()}

    # Group actions by resource
    @staticmethod
    def __getResourceWiseTransactions(actionPlan):
        resourceWiseActions = collections.defaultdict(list)
        for agent in actionPlan:
            for action in actionPlan[agent]:
                if not isinstance(action, CreateAction):
                    resourceWiseActions[action.resource] += [action]
        return resourceWiseActions

    # Matches order wrt priority
    @staticmethod
    def __processResourceExchange(resource, actions):
        buyActions = filter(lambda x: x.qty > 0, actions)
        sellActions = filter(lambda x: x.qty < 0, actions)

        orderedBuyActions = sorted(buyActions, key=lambda x: -x.price)
        orderedSellActions = sorted(sellActions, key=lambda x: x.price)

        # Cant we achieve better matching in case best buyPrice is much higher than best sellPrice? should be able to fill more orders
        # Example: (assume 1qty oreders)
        #           BuyPrices  - 1 2 3 4 5
        #           SellPrices -       4 5 6 7 8
        # If processing in priority order, matched buy-sell orders: (5,4)
        # If we do something unfair, matched buy-sell orders: (4,4), (5,5)
        # 
        # Also, for price-deltas, we'll assume buyers are dumb and hand over the difference as bonus to sellers
        executionPlan = []
        while orderedBuyActions[0].price > orderedSellActions[0].price:
            bestBuy, bestSell = orderedBuyActions[0], orderedSellActions[0]
            transQty = min(bestBuy.qty, -bestSell.qty)
            executionPlan += [TransactAction(bestBuy.agent,  resource, transQty, bestBuy.price)]
            executionPlan += [TransactAction(bestSell.agent, resource, -transQty, bestBuy.price)]
            
            def updateActionQ(Q, qty):
                if Q[0].qty == qty: Q.pop(0)
                else:               Q[0].qty -= transQty
            updateActionQ(orderedBuyActions, transQty)
            updateActionQ(orderedSellActions, -transQty)

        # How to update the last-prices?
        # We have a continuum of traded prices

        return executionPlan

    # Returns an executionPlan of approved actions
    def simulateExchange(self, actionPlan):
        resourceWiseActions = Market.__getResourceWiseTransactions(actionPlan)

        executionPlan = []
        for resource, actions in resourceWiseActions.items():
            executionPlan += Market.__processResourceExchange(resource, actions)
        return executionPlan


class World:
    agentInfo = {}
    agents = []
    market = None
    resourceGraph = None

    def __init__(self, worldInitializationConfig, agents, resourceGraph):
        self.agents = agents
        self.agentInfo = {}
        for agent in agents:
            self.agentInfo[agent] = {
                'money': worldInitializationConfig['agentMoneyGenerator'](agent),
                'resources': worldInitializationConfig['agentResourceGenerator'](agent, resourceGraph),
                'appetite': worldInitializationConfig['agentAppetiteGenerator'](agent, resourceGraph),
                'capabilities': set()
            }
        self.resourceGraph = resourceGraph
        self.market = Market()

    # All proposed actions are assumed to be <i>valid</i>
    # ie, buy actions will have sufficient money to pay for themselves
    #     sell actions will have sufficient resources to sell
    # and create actions will have sufficient inputs for consuming
    def simulateStep(self, proposedPlan):
        # Creation cannot consume resources bought in current turn
        # Exchanged resources & money is available on next turn only
        createActions = filter(lambda x: isinstance(x, CreateAction), proposedPlan)
        for action in createActions:
            currAgentInfo = self.agentInfo[action.agent]
            inputs = action.resource.getInputs()
            for iResource, iQty in inputs:
                currAgentInfo['resources'][iResource] -= iQty * action.qty
            currAgentInfo['resources'][action.resource] += action.qty

        executedPlan = self.market.simulateExchange(proposedPlan)
        for action in executedPlan:
            currAgentInfo = self.agentInfo[action.agent]
            currAgentInfo['money'] -= action.qty * action.price
            currAgentInfo['resources'][action.resource] += action.qty


"""
    Implementing the actual Simulator 
        (Runs the interactions between the agents & environment)
"""

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
        proposedPlan = []
        for agent in self.agents:
            proposedPlan += agent.plan(self.agentRewards[agent], self.world.agentInfo[agent], self.world.market) # TODO: Define agentRewards

        self.updateWorld(proposedPlan)
        self.turn += 1

    def runSimulation(self, numTurns):
        for _ in numTurns:
            self.runSimulationStep()
