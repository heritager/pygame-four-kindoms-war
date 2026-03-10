MAP_PRESETS = {
    'balanced': {
        'id': 'balanced',
        'name': '均衡大陆',
        'subtitle': '标准平衡资源与地形',
        'terrain': {
            'scale': 6.0,
            'water_threshold': 0.25,
            'mountain_threshold': 0.35,
            'forest_threshold': 0.60,
        },
        'fairness': {
            'max_zone_water_ratio': 0.28,
            'max_zone_mountain_ratio': 0.20,
            'min_zone_plain_ratio': 0.32,
        },
        'city': {
            'min_fill_ratio': 0.50,
            'max_fill_ratio': 1.00,
            'major_ratio': 0.35,
            'forest_small_ratio': 0.30,
        },
        'mine': {
            'min_count': 2,
            'max_count': 3,
            'primary_min_distances': [7, 5, 3],
            'fallback_min_distances': [3, 1, 0],
        },
    },
    'highland': {
        'id': 'highland',
        'name': '高地战区',
        'subtitle': '山地更多，推进更慢',
        'terrain': {
            'scale': 6.8,
            'water_threshold': 0.20,
            'mountain_threshold': 0.42,
            'forest_threshold': 0.67,
        },
        'fairness': {
            'max_zone_water_ratio': 0.24,
            'max_zone_mountain_ratio': 0.30,
            'min_zone_plain_ratio': 0.24,
        },
        'city': {
            'min_fill_ratio': 0.55,
            'max_fill_ratio': 1.00,
            'major_ratio': 0.40,
            'forest_small_ratio': 0.28,
        },
        'mine': {
            'min_count': 2,
            'max_count': 3,
            'primary_min_distances': [6, 5, 3],
            'fallback_min_distances': [3, 1, 0],
        },
    },
    'archipelago': {
        'id': 'archipelago',
        'name': '群岛海战',
        'subtitle': '水域更广，矿点更多',
        'terrain': {
            'scale': 5.4,
            'water_threshold': 0.33,
            'mountain_threshold': 0.42,
            'forest_threshold': 0.68,
        },
        'fairness': {
            'max_zone_water_ratio': 0.42,
            'max_zone_mountain_ratio': 0.18,
            'min_zone_plain_ratio': 0.22,
        },
        'city': {
            'min_fill_ratio': 0.40,
            'max_fill_ratio': 0.75,
            'major_ratio': 0.30,
            'forest_small_ratio': 0.34,
        },
        'mine': {
            'min_count': 3,
            'max_count': 4,
            'primary_min_distances': [6, 4, 2],
            'fallback_min_distances': [2, 1, 0],
        },
    },
}

MAP_PRESET_ORDER = ['balanced', 'highland', 'archipelago']
DEFAULT_MAP_PRESET = MAP_PRESET_ORDER[0]


def _validate_map_preset(preset):
    """校验地图预设的阈值合理性"""
    terrain = preset.get('terrain', {})
    water_threshold = terrain.get('water_threshold', 0.25)
    mountain_threshold = terrain.get('mountain_threshold', 0.35)
    forest_threshold = terrain.get('forest_threshold', 0.60)

    # 校验阈值递增关系
    if not (0 <= water_threshold < mountain_threshold < forest_threshold <= 1):
        raise ValueError(
            f"地图预设 '{preset.get('id', 'unknown')}' 的地形阈值无效："
            f"water_threshold={water_threshold}, mountain_threshold={mountain_threshold}, "
            f"forest_threshold={forest_threshold}. 必须满足 0 <= water < mountain < forest <= 1"
        )

    # 校验 fairness 阈值合理性
    fairness = preset.get('fairness', {})
    max_water = fairness.get('max_zone_water_ratio', 0.28)
    max_mountain = fairness.get('max_zone_mountain_ratio', 0.20)
    min_plain = fairness.get('min_zone_plain_ratio', 0.32)

    if not (0 <= max_water <= 1):
        raise ValueError(f"max_zone_water_ratio 必须在 0-1 之间，当前为 {max_water}")
    if not (0 <= max_mountain <= 1):
        raise ValueError(f"max_zone_mountain_ratio 必须在 0-1 之间，当前为 {max_mountain}")
    if not (0 <= min_plain <= 1):
        raise ValueError(f"min_zone_plain_ratio 必须在 0-1 之间，当前为 {min_plain}")
    if max_water + max_mountain + min_plain > 1.5:  # 宽松检查，避免过度约束
        raise ValueError(
            f"fairness 阈值之和过大：water={max_water}, mountain={max_mountain}, plain={min_plain}"
        )

    # 校验 city 配置
    city = preset.get('city', {})
    min_fill = city.get('min_fill_ratio', 0.50)
    max_fill = city.get('max_fill_ratio', 1.00)
    if not (0 <= min_fill <= max_fill <= 1):
        raise ValueError(
            f"city 配置无效：min_fill_ratio={min_fill}, max_fill_ratio={max_fill}. "
            f"必须满足 0 <= min_fill <= max_fill <= 1"
        )

    # 校验 mine 配置
    mine = preset.get('mine', {})
    min_count = mine.get('min_count', 2)
    max_count = mine.get('max_count', 3)
    if min_count < 0 or max_count < min_count:
        raise ValueError(
            f"mine 配置无效：min_count={min_count}, max_count={max_count}. "
            f"必须满足 min_count >= 0 且 max_count >= min_count"
        )

    return True


def get_map_preset(preset_id):
    if preset_id in MAP_PRESETS:
        preset = MAP_PRESETS[preset_id]
        _validate_map_preset(preset)  # 校验配置有效性
        return preset
    return MAP_PRESETS[DEFAULT_MAP_PRESET]
