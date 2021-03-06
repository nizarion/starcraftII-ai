import sc2, random
from sc2 import run_game, maps, Race, Difficulty
from sc2.player import Bot, Computer
from sc2.constants import NEXUS, PROBE, PYLON, ASSIMILATOR, GATEWAY, \
CYBERNETICSCORE, STALKER, STARGATE, VOIDRAY, ROBOTICSFACILITY, IMMORTAL
from  examples.protoss.cannon_rush import CannonRushBot
from examples.terran.proxy_rax import ProxyRaxBot

# 165 iteration per minute
                                                                                

class SentdeBot(sc2.BotAI):

    def __init__(self):
        self.ITERATIONS_PER_MINUTE = 165
        self.MAX_WORKERS = 70

    async def on_step(self, iteration):
        self.itereration = iteration  # give access everywhere in here
        self.minutes = self.itereration / self.ITERATIONS_PER_MINUTE
        # what to do every step
        await self.distribute_workers()  # in sc2/bot_ai.py
        await self.build_workers()  # workers bc obviously
        await self.build_pylons()  # pylons are protoss supply buildings
        await self.build_assimilator()  # getting gas
        await self.expand()  # expand to a new resource area.
        await self.offensive_force_buildings()
        await self.build_offensive_force()
        await self.attack()

    async def build_workers(self):
        # nexus = command center
        if len(self.units(NEXUS)) * 16 > len(self.units(PROBE)) and \
        len(self.units(PROBE)) < self.MAX_WORKERS:
            for nexus in self.units(NEXUS).ready.noqueue:
                # we want at least 20 workers, otherwise let's allocate 
                # 70% of our supply to workers. Later we should use
                # some sort of regression algo maybe for this?
                if self.can_afford(PROBE):
                    await self.do(nexus.train(PROBE))

    async def build_pylons(self):
        if self.supply_left < 5 and not self.already_pending(PYLON):
            nexuses = self.units(NEXUS).ready
            if nexuses.exists:
                if self.can_afford(PYLON):
                    await self.build(PYLON, near=nexuses.first)

    async def build_assimilator(self):
        for nexus in self.units(NEXUS).ready:
            vaspenes = self.state.vespene_geyser.closer_than(10.0, nexus)
            for vaspene in vaspenes:
                if not self.can_afford(ASSIMILATOR):
                    break
                worker = self.select_build_worker(vaspene.position)
                if worker is None:
                    break
                if not self.units(ASSIMILATOR).closer_than(1.0, vaspene).exists:
                    await self.do(worker.build(ASSIMILATOR, vaspene))

    async def expand(self):
        if self.units(NEXUS).amount < (self.minutes / 3 + 1) and self.can_afford(NEXUS):
            await self.expand_now()

    async def offensive_force_buildings(self):
        if self.units(PYLON).ready.exists:
            pylon = self.units(PYLON).ready.random
            
            if self.units(GATEWAY).ready.exists and not self.units(CYBERNETICSCORE):
                if self.can_afford(CYBERNETICSCORE) and not self.already_pending(CYBERNETICSCORE):
                    await self.build(CYBERNETICSCORE, near=pylon)
            elif len(self.units(GATEWAY)) < 3 * self.units(NEXUS).amount:
                if self.can_afford(GATEWAY) and not self.already_pending(GATEWAY):
                    await self.build(GATEWAY, near=pylon)
                    
            if self.units(CYBERNETICSCORE).ready.exists:
#                 if len(self.units(STARGATE)) < self.units(NEXUS).amount / 3 + 1:
#                     if self.can_afford(STARGATE) and not self.already_pending(STARGATE):
#                         await self.build(STARGATE, near=pylon)
                if len(self.units(ROBOTICSFACILITY)) < self.units(NEXUS).amount / 3:
                    if self.can_afford(ROBOTICSFACILITY) and not self.already_pending(ROBOTICSFACILITY):
                        await self.build(ROBOTICSFACILITY, near=pylon)

    async def build_offensive_force(self):
        for sg in self.units(STARGATE).ready.noqueue:
            if self.can_afford(VOIDRAY) and self.supply_left > 0:
                await self.do(sg.train(VOIDRAY))
                
        for rb in self.units(ROBOTICSFACILITY).ready.noqueue:
            if self.can_afford(IMMORTAL) and self.supply_left > 0 and\
             self.units(ROBOTICSFACILITY).ready.exists:
                await self.do(rb.train(IMMORTAL))      
                  
        for gw in self.units(GATEWAY).ready.noqueue:
            if not self.units(STALKER).amount > 2 * self.units(IMMORTAL).amount:
                if self.can_afford(STALKER) and self.supply_left > 0 and\
                 self.units(CYBERNETICSCORE).ready.exists:
                    await self.do(gw.train(STALKER))

    def find_target(self, state):
        if len(self.known_enemy_units) > 0:
            return random.choice(self.known_enemy_units)
        elif len(self.known_enemy_structures) > 0:
            return random.choice(self.known_enemy_structures)
        else:
            return self.enemy_start_locations[0]

    async def attack(self):
        # {UNIT: [n to fight, n to defend]}
        aggressive_units = {STALKER: [15, 5],
                            VOIDRAY: [8, 3],
                            IMMORTAL: [5, 2]}

        for UNIT in aggressive_units:
            if self.units(UNIT).amount > aggressive_units[UNIT][0] and self.units(UNIT).amount > aggressive_units[UNIT][1]:
                for s in self.units(UNIT).idle:
                    await self.do(s.attack(self.find_target(self.state)))

            elif self.units(UNIT).amount > aggressive_units[UNIT][1]:
                if len(self.known_enemy_units) > 0:
                    for s in self.units(UNIT).idle:
                        await self.do(s.attack(random.choice(self.known_enemy_units)))


run_game(maps.get("(2)CatalystLE"), [
    Bot(Race.Protoss, SentdeBot()),
    Computer(Race.Zerg, Difficulty.Hard)
], realtime=False)
