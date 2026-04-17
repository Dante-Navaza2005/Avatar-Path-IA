import unittest

from avatar_path.config import load_config
from avatar_path.map_loader import load_map
from avatar_path.planner import JourneyPlanner, compare_search_algorithms
from avatar_path.team_planner import TeamPlanner
from avatar_path.visualization import build_animation_frames


class JourneyPlannerTests(unittest.TestCase):
    def test_map_matches_expected_dimensions_and_checkpoints(self):
        """Confirma que o mapa carregado bate com o formato exigido no enunciado."""

        config = load_config("config/default_config.json")
        map_data = load_map(config)

        self.assertEqual(
            map_data.height,
            82,
            "Altura inesperada para o mapa carregado.",
        )
        self.assertEqual(
            map_data.width,
            300,
            "Largura inesperada para o mapa carregado.",
        )
        self.assertEqual(
            len(map_data.checkpoints),
            len(config.checkpoint_order),
            "Nem todos os checkpoints esperados foram encontrados no mapa.",
        )
        self.assertEqual(
            map_data.cell(map_data.checkpoints["0"]),
            "0",
            "A coordenada registrada para o checkpoint inicial nao aponta para o simbolo '0'.",
        )
        self.assertEqual(
            map_data.cell(map_data.checkpoints["Z"]),
            "Z",
            "A coordenada registrada para o checkpoint final nao aponta para o simbolo 'Z'.",
        )

    def test_team_planner_respects_energy_limits(self):
        """Verifica se a combinatoria respeita energia, etapas e custo esperado."""

        config = load_config("config/default_config.json")
        planner = TeamPlanner(config.characters, config.checkpoint_order[1:], config.stage_difficulties)

        assignments, usage, total_cost = planner.optimize()

        self.assertEqual(
            len(assignments),
            31,
            "A quantidade de etapas planejadas nao bate com a jornada configurada.",
        )
        self.assertEqual(
            round(total_cost, 4),
            1805.5486,
            "O custo combinatorio mudou em relacao ao resultado esperado.",
        )
        self.assertTrue(
            all(count <= 8 for count in usage.values()),
            f"Algum personagem excedeu o limite de energia: {usage}",
        )
        self.assertEqual(
            sum(usage.values()),
            56,
            "A energia total usada pelas equipes nao bate com o esperado.",
        )
        self.assertEqual(
            assignments[0].stage_symbol,
            "1",
            "A primeira etapa combinatoria deveria comecar no checkpoint '1'.",
        )
        self.assertEqual(
            assignments[-1].stage_symbol,
            "Z",
            "A ultima etapa combinatoria deveria terminar no checkpoint 'Z'.",
        )

    def test_full_journey_default_result(self):
        """Garante que a solucao completa continua igual no caso padrao do trabalho."""

        config = load_config("config/default_config.json")
        result = JourneyPlanner(config).solve()

        self.assertEqual(
            len(result.segments),
            31,
            "A jornada completa deveria conter 31 trechos entre checkpoints consecutivos.",
        )
        self.assertEqual(
            result.movement_cost,
            2798,
            "O custo de movimento do A* mudou em relacao ao resultado esperado.",
        )
        self.assertEqual(
            round(result.stage_cost, 4),
            1805.5486,
            "O custo combinatorio agregado da jornada mudou em relacao ao esperado.",
        )
        self.assertEqual(
            round(result.total_cost, 4),
            4603.5486,
            "O custo total final mudou em relacao ao resultado esperado.",
        )
        self.assertEqual(
            result.segments[0].start_symbol,
            "0",
            "A jornada deveria iniciar no checkpoint '0'.",
        )
        self.assertEqual(
            result.segments[-1].end_symbol,
            "Z",
            "A jornada deveria terminar no checkpoint 'Z'.",
        )

    def test_animation_frames_cover_start_and_finish(self):
        """Confirma que a animacao preserva os custos do inicio ao fim da jornada."""

        config = load_config("config/default_config.json")
        result = JourneyPlanner(config).solve()
        frames = build_animation_frames(result)

        self.assertEqual(
            frames[0].movement_cost,
            0,
            "O primeiro frame deveria iniciar sem custo de movimento acumulado.",
        )
        self.assertEqual(
            frames[0].stage_cost,
            0.0,
            "O primeiro frame deveria iniciar sem custo combinatorio acumulado.",
        )
        self.assertEqual(
            frames[-1].movement_cost,
            result.movement_cost,
            "O ultimo frame nao reproduz o custo final de movimento.",
        )
        self.assertEqual(
            round(frames[-1].stage_cost, 4),
            round(result.stage_cost, 4),
            "O ultimo frame nao reproduz o custo final das etapas.",
        )
        self.assertEqual(
            round(frames[-1].total_cost, 4),
            round(result.total_cost, 4),
            "O ultimo frame nao reproduz o custo total final.",
        )
        self.assertEqual(
            frames[0].coordinate,
            result.map_data.checkpoints["0"],
            "O primeiro frame nao comeca no checkpoint inicial.",
        )
        self.assertEqual(
            frames[-1].coordinate,
            result.map_data.checkpoints["Z"],
            "O ultimo frame nao termina no checkpoint final.",
        )

    def test_search_comparison_prefers_astar(self):
        """Compara os algoritmos de busca e garante que o A* segue como referencia."""

        config = load_config("config/default_config.json")
        comparison = compare_search_algorithms(config)

        self.assertEqual(
            comparison[0]["algorithm"],
            "astar",
            f"O melhor algoritmo deveria ser o A*, mas foi {comparison[0]['algorithm']}.",
        )
        self.assertEqual(
            comparison[0]["movement_cost"],
            2798,
            "O custo de movimento do A* na comparacao nao bate com o esperado.",
        )
        self.assertEqual(
            round(comparison[0]["total_cost"], 4),
            4603.5486,
            "O custo total do A* na comparacao nao bate com o esperado.",
        )
        self.assertGreater(
            comparison[-1]["movement_cost"],
            comparison[0]["movement_cost"],
            "Esperava-se que o pior algoritmo expandisse um caminho mais caro que o A*.",
        )
        self.assertEqual(
            {item["algorithm"] for item in comparison},
            {"astar", "dijkstra", "greedy"},
            "A comparacao deveria conter exatamente os tres algoritmos configurados.",
        )


if __name__ == "__main__":
    unittest.main()
