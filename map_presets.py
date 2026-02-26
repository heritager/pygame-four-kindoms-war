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


def get_map_preset(preset_id):
    if preset_id in MAP_PRESETS:
        return MAP_PRESETS[preset_id]
    return MAP_PRESETS[DEFAULT_MAP_PRESET]
