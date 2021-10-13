import random
import numpy as np
import collections

import gym.spaces
from ray.rllib.env import MultiAgentEnv

#ConfigStart
def agentMoneyGenerator(agent):
    return random.randint(10,99)

def agentResourceGenerator(agent, resourceGraph):
    return {
        resource : random.randint(10,999)
            for resource in resourceGraph.resourceArray()
    }

def agentAppetiteGenerator(agent, resourceGraph):
    return {
        resource: 1
            for resource in resourceGraph.resourceArray()
    }

gameConfig = {
    "numAgents": 3,
    "money": agentMoneyGenerator,
    "resources": agentResourceGenerator,
    "appetite": agentAppetiteGenerator
}
#ConfigEnd

"""
    Modelling Actors in our simulation
        (Serves as a wrapper for the RI algo)
"""

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
            if proposedPrice < agentInfo['money'] and proposedPrice > 0:
                proposedQty = 1 + random.randrange(agentInfo['money'] // proposedPrice)
                buyActions += [TransactAction(self, resource, proposedQty, proposedPrice)]

            # Add possible create action
            resourceInputs = ResourceGraph.getInputs(resource)
            if len(resourceInputs) == 0:
                creatableQty = 10
            else:
                creatableQty = min(agentInfo['resources'][iResource] // iQty for iResource, iQty in resourceInputs)

            if creatableQty > 0:
                proposedQty = 1 + random.randrange(creatableQty)
                createActions += [CreateAction(self, resource, proposedQty)]

            if agentInfo['resources'][resource] > 0:
                proposedQty = 1 + random.randrange(agentInfo['resources'][resource])
                
                # Add possible sell action
                sellActions += [TransactAction(self, resource, -proposedQty, proposedPrice)]

                # Add possible consume action
                consumeActions += [ConsumeAction(self, resource, proposedQty)]

        allActions = consumeActions + createActions + buyActions + sellActions
        random.shuffle(allActions)

        return [allActions[0]]

    # Returns list of actions: buy / sell / create
    # First cut: Choose randomly from among set of all possible actions, will choose only 1 per turn
    def plan(self, reward, agentInfo, market):
        return self.__genRandomAction(agentInfo, market)


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
        super().__init__(agent, resource, qty)

# negative qty is selling for agent
class TransactAction(Action):
    def __init__(self, agent, resource, qty, price):
        super().__init__(agent, resource, qty)
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

    @staticmethod
    def resourceArray():
        return [0, 1]

    @staticmethod
    def getInputs(resourceName):
        if resourceName == 0:
            return []
        else:
            return [(0, 2)]
    
    @staticmethod
    def GetNumResources():
        return 2

class Market:
    
    def __init__(self, resourceGraph):
        self.lastPrices = {resource : random.randint(10,49) for resource in resourceGraph.resourceArray()}

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

        print("***MarketExchange***")
        best_buy, best_sell = max([x.price for x in orderedBuyActions]+[0]), min([x.price for x in orderedSellActions]+[0])
        print("#Buys=%d, #Sells=%d, Best-Buy=%.2f, Best-Sell=%.2f" % (len(orderedBuyActions), len(orderedSellActions), best_buy, best_sell))

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
        while len(orderedBuyActions) > 0 and len(orderedSellActions) > 0 \
                and orderedBuyActions[0].price > orderedSellActions[0].price:

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
                'money': worldInitializationConfig['money'](agent),
                'resources': worldInitializationConfig['resources'](agent, resourceGraph),
                'appetite': worldInitializationConfig['appetite'](agent, resourceGraph),
                'lastReward': 0,
                'netReward': 0
            }
        self.resourceGraph = resourceGraph
        self.market = Market(self.resourceGraph)

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
                    for iResource, iQty in ResourceGraph.getInputs(action.resource):
                        resourceReqs[iResource] += iQty * action.qty
                elif isinstance(action, ConsumeAction):
                    resourceReqs[action.resource] += action.qty
            
            currAgentInfo = self.agentInfo[agent]
            if currAgentInfo['money'] >= moneyReqs and \
                all(currAgentInfo["resources"][resource] >= resourceQty for resource, resourceQty in resourceReqs.items()):
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
        createActions = list(filter(lambda x: isinstance(x, CreateAction), proposedPlan))
        for action in createActions:
            currAgentInfo = self.agentInfo[action.agent]
            inputs = ResourceGraph.getInputs(action.resource)
            for iResource, iQty in inputs:
                currAgentInfo['resources'][iResource] -= iQty * action.qty
            currAgentInfo['resources'][action.resource] += action.qty

        consumeActions = list(filter(lambda x: isinstance(x, ConsumeAction), proposedPlan))
        for action in consumeActions:
            currAgentInfo = self.agentInfo[action.agent]
            currAgentInfo['resources'][action.resource] -= action.qty
            currAgentInfo['lastReward'] += currAgentInfo['appetite'][action.resource] * action.qty

        executedPlan = list(self.market.simulateExchange(proposedPlan))
        for action in executedPlan:
            currAgentInfo = self.agentInfo[action.agent]
            currAgentInfo['money'] -= action.qty * action.price
            currAgentInfo['lastReward'] -= action.qty * action.price
            currAgentInfo['resources'][action.resource] += action.qty

        print ("Executed: %d Create, %d Consume, %d Transact" % (len(createActions), len(consumeActions), len(executedPlan)/2))

        for agent in self.agents:
            self.agentInfo[agent]['netReward'] += self.agentInfo[agent]['lastReward']
        print ("Net reward: %d" % sum(self.agentInfo[agent]["lastReward"] for agent in self.agents))

    # Get vectorized state for RL library
    def getAgentState(self, agent):
        return \
        [self.agentInfo[agent]["money"]] + \
        [self.agentInfo[agent]["resources"][resource] for resource in self.resourceGraph.resourceArray()] + \
        [self.agentInfo[agent]["appetite"][resource] for resource in self.resourceGraph.resourceArray()] + \
        [self.market.lastPrices[resource] for resource in self.resourceGraph.resourceArray()]

"""
    TODO - 
    reset: () => new-episode, goto start
    step: (action_dict: agent -> actions) => obs, rew, True, {}

    State-Space: 
        Private-State: (money, resourceQty[N], appetites[N])
        Global-State (public): resourceGraph <- skip for now
        Global-State (partially public): market(=lastPrice[N])


"""
class WorldEnv(MultiAgentEnv):
    def __init__(self, return_agent_actions = False, part=False):
        self.num_agents = 5
        self.agents = ["agent-%d" % idx for idx in range(self.num_agents)]
        self.num_resources = ResourceGraph.GetNumResources()
        self.world = None

        """
        State-Space: [Money, Inventory[N], Appetite[N], lastPrices[N]]
        """
        self.observation_space = gym.spaces.MultiDiscrete(
            [1000] + \
            [1000 for _ in range(self.num_resources)] + \
            [10 for _ in range(self.num_resources)] + \
            [50 for _ in range(self.num_resources)])

        """
        Action-Space: [{buy,sell,create,consume}, {N resources}, {qty}, {price if buy/sell}]
            one action taken per chance
            action will be invalidated if impossible
        """
        self.action_space = gym.spaces.MultiDiscrete([4, self.num_resources, 10, 50])

    def reset(self):
        self.world = World(gameConfig, self.agents, ResourceGraph())
        return {
            agent: self.world.getAgentState(agent)
                for agent in self.agents
        }

    def step(self, action_dict):
        
        def buildActionObj(agent, a):
            if a[0] == 0:
                return CreateAction(agent, a[1], a[2])
            elif a[0] == 1:
                return TransactAction(agent, a[1], a[2], a[3])
            elif a[0] == 2:
                return TransactAction(agent, a[1], -a[2], a[3])
            else:
                return ConsumeAction(agent, a[1], a[2])

        proposedPlan = [buildActionObj(agent, action_dict[agent]) for agent in action_dict]
        self.world.updateWorld(proposedPlan)

        obs, rew, done, info = {}, {}, {}, {}
        for idx, agent_id in enumerate(self.agents):
            obs[idx], rew[idx], done[idx], info[idx] = self.world.getAgentState(agent_id), self.world.agentInfo[agent_id]["lastReward"], True, {}

        done["__all__"] = True
        return obs, rew, done, info


"""
    Implementing the actual Simulator 
        (Runs the interactions between the agents & environment)
"""
# class Simulator:

#     def __init__(self, worldInitializationConfig, resourceGraph):
#         self.resourceGraph = resourceGraph
#         self.agents = [Agent(x) for x in range(worldInitializationConfig['numAgents'])]
#         self.world = World(worldInitializationConfig, self.agents, resourceGraph)
#         self.turn = 0

#     def runSimulationStep(self):
#         proposedPlan = []
#         for agent in self.agents:
#             proposedPlan += agent.plan(self.world.agentInfo[agent]['lastReward'], self.world.agentInfo[agent], self.world.market)

#         self.world.updateWorld(proposedPlan)
#         self.turn += 1

#     def runSimulation(self, numTurns):
#         for _ in range(numTurns):
#             self.runSimulationStep()


if __name__=="__main__":
    # sim = Simulator(gameConfig, ResourceGraph())
    # sim.runSimulation(100)
    pass
