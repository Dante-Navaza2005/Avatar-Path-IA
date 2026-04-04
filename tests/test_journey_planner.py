import unittest

from avatar_path.config import load_config
from avatar_path.map_loader import load_map
from avatar_path.pathfinding import find_path
from avatar_path.planner import JourneyPlanner, compare_search_algorithms, optimize_checkpoint_order
from avatar_path.team_planner import TeamPlanner
from avatar_path.visualization import build_animation_frames


class JourneyPlannerTests(unittest.TestCase):
    def test_optimize_checkpoint_order_keeps_endpoints_and_reduces_movement(self):
        config = load_config("config/default_config.json")
        map_data = load_map(config)

        optimized_order = optimize_checkpoint_order(map_data, config.checkpoint_order, "astar")

        self.assertEqual(optimized_order[0], config.checkpoint_order[0])
        self.assertEqual(optimized_order[-1], config.checkpoint_order[-1])
        self.assertEqual(len(set(optimized_order)), len(config.checkpoint_order))

        def movement_cost(order: tuple[str, ...]) -> int:
            total = 0
            for idx in range(len(order) - 1):
                blocked = frozenset(
                    map_data.checkpoints[symbol]
                    for symbol in order[idx + 2 :]
                )
                _, segment_cost, _ = find_path(
                    map_data,
                    map_data.checkpoints[order[idx]],
                    map_data.checkpoints[order[idx + 1]],
                    "astar",
                    blocked,
                )
                total += segment_cost
            return total

        self.assertLess(movement_cost(optimized_order), movement_cost(config.checkpoint_order))

    def test_map_matches_expected_dimensions_and_checkpoints(self):
        config = load_config("config/default_config.json")
        map_data = load_map(config)

        self.assertEqual(map_data.height, 82)
        self.assertEqual(map_data.width, 300)
        self.assertEqual(len(map_data.checkpoints), len(config.checkpoint_order))

    def test_team_planner_respects_energy_limits(self):
        config = load_config("config/default_config.json")
        planner = TeamPlanner(config.characters, config.checkpoint_order[1:-1], config.stage_difficulties)

        assignments, usage, total_cost = planner.optimize()

        self.assertEqual(len(assignments), 30)
        self.assertEqual(round(total_cost, 4), 1638.1436)
        self.assertTrue(all(count <= 8 for count in usage.values()))
        self.assertEqual(sum(usage.values()), 56)

    def test_full_journey_default_result(self):
        config = load_config("config/default_config.json")
        result = JourneyPlanner(config).solve()

        self.assertEqual(len(result.segments), 31)
        self.assertEqual(result.movement_cost, 1815)
        self.assertEqual(round(result.stage_cost, 4), 1638.1436)
        self.assertEqual(round(result.total_cost, 4), 3453.1436)

    def test_animation_frames_cover_start_and_finish(self):
        config = load_config("config/default_config.json")
        result = JourneyPlanner(config).solve()
        frames = build_animation_frames(result)

        self.assertEqual(frames[0].movement_cost, 0)
        self.assertEqual(frames[0].stage_cost, 0.0)
        self.assertEqual(frames[-1].movement_cost, result.movement_cost)
        self.assertEqual(round(frames[-1].stage_cost, 4), round(result.stage_cost, 4))
        self.assertEqual(round(frames[-1].total_cost, 4), round(result.total_cost, 4))

    def test_search_comparison_prefers_astar(self):
        config = load_config("config/default_config.json")
        comparison = compare_search_algorithms(config)

        self.assertEqual(comparison[0]["algorithm"], "astar")
        self.assertEqual(comparison[0]["movement_cost"], 2807)
        self.assertEqual(round(comparison[0]["total_cost"], 4), 4445.1436)
        self.assertGreater(comparison[-1]["movement_cost"], comparison[0]["movement_cost"])


if __name__ == "__main__":
    unittest.main()
