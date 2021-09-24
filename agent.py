import random
import numpy as np
import collections

"""
    Modelling Actors in our simulation
        (Serves as a wrapper for the RI algo)
"""

# TODO - definev gov agents
# class GovernmentAgent:
#     pass

class Agent:
    def __init__(self, id):
        self.id = id

    # Qty & prices will be chosen randomly
    def __genRandomAction(self, agentInfo, market):
        consumeActions, createActions = [], []
        buyActions, sellActions = [], []
        
        for resource in agentInfo['resources']:
            # Add possible buy action
            proposedPrice = int( np.random.normal(market.lastPrices[resource], market.lastPrices[resource]/4) )
            proposedQty = 1 + random.randrange(agentInfo['money'] // proposedPrice)
            buyActions += [TransactAction(self, resource, proposedQty, proposedPrice)]

            # Add possible create action
            creatableQty = min(agentInfo['resources'][iResource] // iQty for iResource, iQty in resource.getInputs())
            if creatableQty > 0:
                proposedQty = 1 + random.rangrange(creatableQty)
                createActions += [CreateAction(self, resource, proposedQty)]

            if agentInfo['resources'][resource] > 0:
                proposedQty = 1 + random.randrange(agentInfo['resources'][resource])
                
                # Add possible sell action
                sellActions += [TransactAction(self, resource, proposedQty, proposedPrice)]

                # Add possible consume action
                consumeActions += [ConsumeAction(self, resource, proposedQty)]

        allActions = consumeActions + createActions + buyActions + sellActions
        random.shuffle(allActions)

        return [allActions[0]]

    # Returns list of actions: buy / sell / create
    # First cut: Choose randomly from among set of all possible actions, will choose only 1 per turn
    def plan(self, reward, agentInfo, market):
        return self.__genRandomAction()


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
        super().__init__(self, agent, resource, qty)

# negative qty is selling for agent
class TransactAction(Action):
    def __init__(self, agent, resource, qty, price):
        super().__init__(self, agent, resource, qty)
        self.price = price

class ConsumeAction(Action):
    def __init__(self, agent, resource, qty):
        super().__init__(agent, resource, qty)

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


# TODO - define resourceGraph
class ResourceGraph:

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
        for action in actionPlan:
            if isinstance(action, TransactAction):
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
        bestBuy, bestSell = None, None
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

        return executionPlan, bestBuy.price if bestBuy != None else None

    # Returns an executionPlan of approved actions
    def simulateExchange(self, actionPlan):
        resourceWiseActions = Market.__getResourceWiseTransactions(actionPlan)

        executionPlan = []
        for resource, actions in resourceWiseActions.items():
            executedActions, lastPrice = Market.__processResourceExchange(resource, actions)
            executionPlan += executedActions
            if lastPrice != None:
                self.lastPrices[resource] = lastPrice 
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
                'capabilities': set(),
                'lastReward': 0,
                'netReward': 0
            }
        self.resourceGraph = resourceGraph
        self.market = Market()

    # Group actions by agent
    @staticmethod
    def __getAgentWiseTransactions(actionPlan):
        agentWiseActions = collections.defaultdict(list)
        for action in actionPlan:
            agentWiseActions[action.agent] += [action]
        return agentWiseActions

    # All proposed actions should be <i>valid</i>
    # ie, buy actions will have sufficient money to pay for themselves
    #     sell actions will have sufficient resources to sell
    # and create actions will have sufficient inputs for consuming
    # 
    # PS: Bad actors will have all their proposed actions revoked, 
    #     I cant be bothered to find maximal set of proposed actions that can be valid given agents stuff
    def __filterInvalidActions(self, actionPlan):
        agentWiseActions = World.__getAgentWiseTransactions(actionPlan)
        validActions = []
        for agent, actions in agentWiseActions.items():
            resourceReqs = collections.defaultdict(int)
            moneyReqs = 0
            for action in actions:
                if isinstance(action, TransactAction) and action.qty > 0:
                    moneyReqs += action.qty * action.price
                elif isinstance(action, TransactAction):
                    resourceReqs[action.resource] += action.qty
                elif isinstance(action, CreateAction):
                    for iResource, iQty in action.resource.getInputs():
                        resourceReqs[iResource] += iQty * action.qty
                elif isinstance(action, ConsumeAction):
                    resourceReqs[action.resource] += action.qty
            
            currAgentInfo = self.agentInfo[agent]
            if currAgentInfo['money'] >= moneyReqs and \
                all(currAgentInfo[resource] >= resourceQty for resource, resourceQty in resourceReqs.items()):
                validActions += actions
        return validActions

    def updateWorld(self, proposedPlan):
        # Rewards will be computed as happiness from satisified appetite + net-money gain
        for agent in self.agents:
            self.agentInfo[agent]['lastReward'] = 0

        # Remove actions that impossible for an agent to execute
        proposedPlan = self.__filterInvalidActions(proposedPlan)

        # Creation cannot consume resources bought in current turn
        # Exchanged resources & money is available on next turn only
        createActions = filter(lambda x: isinstance(x, CreateAction), proposedPlan)
        for action in createActions:
            currAgentInfo = self.agentInfo[action.agent]
            inputs = action.resource.getInputs()
            for iResource, iQty in inputs:
                currAgentInfo['resources'][iResource] -= iQty * action.qty
            currAgentInfo['resources'][action.resource] += action.qty

        consumeActions = filter(lambda x: isinstance(x, ConsumeAction), proposedPlan)
        for action in consumeActions:
            currAgentInfo = self.agentInfo[action.agent]
            currAgentInfo['resources'][action.resource] -= action.qty
            currAgentInfo['lastReward'] += currAgentInfo['appetite'][action.resource] * action.qty

        executedPlan = self.market.simulateExchange(proposedPlan)
        for action in executedPlan:
            currAgentInfo = self.agentInfo[action.agent]
            currAgentInfo['money'] -= action.qty * action.price
            currAgentInfo['lastReward'] -= action.qty * action.price
            currAgentInfo['resources'][action.resource] += action.qty

        for agent in self.agents:
            self.agentInfo[agent]['netReward'] += self.agentInfo[agent]['lastReward']


"""
    Implementing the actual Simulator 
        (Runs the interactions between the agents & environment)
"""

# TODO - define gameConfig
class GameConfig:
    pass

class Simulator:

    def __init__(self, worldInitializationConfig, resourceGraph):
        self.resourceGraph = resourceGraph
        self.agents = [Agent(x) for x in range(worldInitializationConfig['numAgents'])]
        self.world = World(worldInitializationConfig, self.agents, resourceGraph)
        self.agentRewards = {agent: 0 for agent in self.agents}
        self.turn = 0

    def runSimulationStep(self):
        proposedPlan = []
        for agent in self.agents:
            proposedPlan += agent.plan(self.world.agentInfo[agent]['lastReward'], self.world.agentInfo[agent], self.world.market)

        self.updateWorld(proposedPlan)
        self.turn += 1

    def runSimulation(self, numTurns):
        for _ in numTurns:
            self.runSimulationStep()
