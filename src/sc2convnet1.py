import sc2, random, cv2, numpy as np
from sc2 import run_game, maps, Race, Difficulty, game_data
from sc2.player import Bot, Computer
from sc2.constants import NEXUS, PROBE, PYLON, ASSIMILATOR, GATEWAY, \
CYBERNETICSCORE, STALKER, STARGATE, VOIDRAY, ROBOTICSFACILITY, IMMORTAL, \
OBSERVER
from  examples.protoss.cannon_rush import CannonRushBot
from examples.terran.proxy_rax import ProxyRaxBot

# 165 iteration per minute
                                                                                

class SentdeBot(sc2.BotAI):

    def __init__(self):
        self.ITERATIONS_PER_MINUTE = 165
        self.MAX_WORKERS = 70
        self.draw_dict = {}

    async def on_step(self, iteration):
        self.iteration = iteration  # give access everywhere in here
        self.minutes = self.iteration / self.ITERATIONS_PER_MINUTE
        # what to do every step
        await self.distribute_workers()  # in sc2/bot_ai.py
        await self.build_workers()  # workers bc obviously
        await self.build_pylons()  # pylons are protoss supply buildings
        await self.build_assimilator()  # getting gas
        await self.expand()  # expand to a new resource area.
        await self.offensive_force_buildings()
        await self.build_offensive_force()
        await self.intel()
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
            elif len(self.units(GATEWAY)) < 1:
                if self.can_afford(GATEWAY) and not self.already_pending(GATEWAY):
                    await self.build(GATEWAY, near=pylon)
                    
            if self.units(CYBERNETICSCORE).ready.exists:
                if len(self.units(STARGATE)) < self.minutes:  # this too
                    if self.can_afford(STARGATE) and not self.already_pending(STARGATE):
                        await self.build(STARGATE, near=pylon)

    async def build_offensive_force(self):
        for sg in self.units(STARGATE).ready.noqueue:
            if self.can_afford(VOIDRAY) and self.supply_left > 0:
                await self.do(sg.train(VOIDRAY))

    def find_target(self, state):
        if len(self.known_enemy_units) > 0:
            return random.choice(self.known_enemy_units)
        elif len(self.known_enemy_structures) > 0:
            return random.choice(self.known_enemy_structures)
        else:
            return self.enemy_start_locations[0]
    
    async def intel(self):
        # for game_info: https://github.com/Dentosal/python-sc2/blob/master/sc2/game_info.py#L162
        # print(self.game_info.map_size)
        # flip around. It's y, x when you're dealing with an array.
        # print(dir(self.units(NEXUS)))
        game_data = np.zeros((self.game_info.map_size[1], self.game_info.map_size[0], 3), np.uint8)
        
        self.draw_circle(game_data, 0)
        self.draw_circle(game_data, 1)
#         for unit in self.units().ready:
#             name = unit.name.lower()
#             id = unit.type_id.value
#             if not name in self.draw_dict:
#                 self.draw_dict[name] = [int(unit.radius * 4), (random.randint(0, 255), random.randint(0, 255), 0)]  # random.randint(0, 5) (id % 255, id // 255 * 32, 0)
#             pos = unit.position
#             # print(pos)
#             cv2.circle(game_data, (int(pos[0]), int(pos[1])), self.draw_dict[name][0], self.draw_dict[name][1], -1)  # BGR 
#                
#         for unit in self.known_enemy_units:
#             name = unit.name.lower()
#             id = unit.type_id.value
#             if not name in self.draw_dict:
#                 self.draw_dict[name] = [int(unit.radius * 4), (random.randint(0, 255), random.randint(0, 255), 255)]  # random.randint(0, 5) (id % 255, id // 255 * 32, 0)
#             pos = unit.position
#             # print(pos)
#             cv2.circle(game_data, (int(pos[0]), int(pos[1])), self.draw_dict[name][0], self.draw_dict[name][1], -1)  # BGR 
            
        # flip horizontally to make our final fix in visual representation:
        flipped = cv2.flip(game_data, 0)
        resized = cv2.resize(flipped, dsize=None, fx=2, fy=2)

        cv2.imshow('Intel', resized)
        cv2.waitKey(1)

    async def attack(self):
        # {UNIT: [n to fight, n to defend]}
        aggressive_units = {VOIDRAY: [8, 3]}
        for UNIT in aggressive_units:
            if self.units(UNIT).amount > aggressive_units[UNIT][0] and self.units(UNIT).amount > aggressive_units[UNIT][1]:
                for s in self.units(UNIT).idle:
                    await self.do(s.attack(self.find_target(self.state)))

            elif self.units(UNIT).amount > aggressive_units[UNIT][1]:
                if len(self.known_enemy_units) > 0:
                    for s in self.units(UNIT).idle:
                        await self.do(s.attack(random.choice(self.known_enemy_units)))
                
    def draw_circle(self, game_data, is_enemy):
        if is_enemy:
            red_colour = 255
        else:
            red_colour = 0
            
        for unit in (self.known_enemy_units if is_enemy else self.units().ready):
            name = unit.name.lower()
            id = unit.type_id.value
            if not name in self.draw_dict:
                self.draw_dict[name] = [int(unit.radius * 4), (random.randint(0, 255), random.randint(0, 255), red_colour)]  # random.randint(0, 5) (id % 255, id // 255 * 32, 0)
            pos = unit.position
            # print(pos)
            cv2.circle(game_data, (int(pos[0]), int(pos[1])), self.draw_dict[name][0], self.draw_dict[name][1], -1)  # BGR 


run_game(maps.get("(2)CatalystLE"), [
    Bot(Race.Protoss, SentdeBot()),
    Computer(Race.Terran, Difficulty.Harder)
], realtime=False)
